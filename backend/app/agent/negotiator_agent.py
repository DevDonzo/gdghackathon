from __future__ import annotations

import json
import logging
import re
from typing import Any

from backend.app.core.config import get_settings
from backend.app.services.negotiation_live import (
    advance_live_policy,
    phrase_live_action,
    phrase_support_action,
)


logger = logging.getLogger(__name__)

ALLOWED_ACTIONS = {
    "push_for_retention",
    "counter_to_target",
    "ask_for_credit_plus_rate_relief",
    "accept_offer",
    "exit_without_accepting",
    "explain_support_goal",
    "provide_available_context",
    "ask_for_escalation",
    "ask_for_concrete_next_step",
    "confirm_task_complete",
    "escalate_or_capture_next_step",
}

SYSTEM_PROMPT = """
You are a live phone negotiator calling on behalf of a customer.
You are speaking directly to a carrier or service representative on a voice call.

Rules:
1. Always call analyze_rep_speech first. Its output tells you the action to take.
2. The action returned by analyze_rep_speech is final. Do not choose a different action.
3. Generate concise, natural spoken language that conveys the determined action.
4. Speak as the customer's representative using first person. Keep responses under 3 sentences.
5. Do not use markdown, bullet points, stage directions, or non-speech formatting.
6. Always call finalize_response last with the exact action string and your spoken text.
7. Do not invent offers, concessions, account facts, or promises not authorized by the action.
8. For telecom negotiations, only mention dollar amounts already returned by analyze_rep_speech.
   If the action is counter_to_target, counter exactly to the target monthly rate.
""".strip()


def run_negotiator_agent(negotiation: dict[str, Any], rep_text: str) -> dict[str, Any]:
    """
    Return the same decision shape as advance_live_policy(), with optional
    agent-generated spoken text. Any agent/tool failure falls back to the
    deterministic policy and phrase generator.
    """
    pending_decision: dict[str, Any] = {}

    try:
        from strands import Agent, tool
    except Exception as error:
        logger.warning("Strands agent unavailable; using deterministic live policy: %s", error)
        return advance_live_policy(negotiation, rep_text)

    @tool
    def analyze_rep_speech(rep_text: str, negotiation_json: str) -> str:
        """
        Run RateDrop's deterministic policy engine against the rep speech.
        Call this first on every turn.
        """
        negotiation_payload = json.loads(negotiation_json)
        decision = advance_live_policy(negotiation_payload, rep_text)
        pending_decision.clear()
        pending_decision.update(decision)
        return json.dumps(_decision_summary(decision, negotiation_payload), default=str)

    @tool
    def finalize_response(action: str, spoken_text: str, completed: bool) -> str:
        """
        Validate and register the final spoken response for the policy action.
        Call this as the last tool before ending.
        """
        if action not in ALLOWED_ACTIONS:
            return f"error: unknown action '{action}'"
        if pending_decision and action != pending_decision.get("action"):
            return f"error: action must remain {pending_decision.get('action')}"
        clean_text = _clean_spoken_text(spoken_text)
        if not clean_text:
            return "error: spoken_text must not be empty"
        unauthorized_money = _unauthorized_money_values(clean_text, pending_decision, negotiation)
        if unauthorized_money:
            return f"error: unauthorized monetary value(s): {', '.join(unauthorized_money)}"
        pending_decision["_agent_text"] = clean_text
        pending_decision["_agent_completed"] = bool(completed)
        return "approved"

    try:
        agent_result = _run_strands_turn(
            tools=[analyze_rep_speech, finalize_response],
            rep_text=rep_text,
            negotiation=negotiation,
        )
    except Exception as error:
        settings = get_settings()
        fallback_model_id = settings.agent_fallback_model_id.strip()
        can_retry_bedrock = (
            settings.normalized_agent_model_provider == "bedrock"
            and fallback_model_id
            and fallback_model_id != settings.agent_model_id
        )
        if not can_retry_bedrock:
            logger.warning("Strands agent turn failed; using deterministic live policy: %s", error)
            return advance_live_policy(negotiation, rep_text)
        logger.warning(
            "Strands agent turn failed on %s; retrying with %s: %s",
            settings.agent_model_id,
            fallback_model_id,
            error,
        )
        pending_decision.clear()
        try:
            agent_result = _run_strands_turn(
                tools=[analyze_rep_speech, finalize_response],
                rep_text=rep_text,
                negotiation=negotiation,
                bedrock_model_id=fallback_model_id,
            )
        except Exception as fallback_error:
            logger.warning("Strands fallback agent turn failed; using deterministic live policy: %s", fallback_error)
            return advance_live_policy(negotiation, rep_text)

    if not pending_decision:
        logger.warning("Strands agent did not call analyze_rep_speech; using deterministic live policy.")
        return advance_live_policy(negotiation, rep_text)

    decision = dict(pending_decision)
    agent_text = decision.pop("_agent_text", None)
    decision.pop("_agent_completed", None)
    result_text = _clean_agent_result_text(agent_result) if not agent_text else None
    if result_text and _unauthorized_money_values(result_text, decision, negotiation):
        result_text = None
    decision["text"] = agent_text or result_text or _fallback_phrase(decision, negotiation)
    return decision


def _run_strands_turn(
    tools: list[Any],
    rep_text: str,
    negotiation: dict[str, Any],
    bedrock_model_id: str | None = None,
) -> Any:
    from strands import Agent

    agent = Agent(
        model=_make_model(bedrock_model_id=bedrock_model_id),
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        callback_handler=None,
    )
    return agent(
        "The representative just said: "
        f"{json.dumps(rep_text)}\n\n"
        f"Negotiation state: {json.dumps(_agent_safe_negotiation(negotiation), default=str)}"
    )


def _make_model(bedrock_model_id: str | None = None) -> Any:
    settings = get_settings()
    if settings.normalized_agent_model_provider == "gemini":
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is required when RATEDROP_AGENT_MODEL_PROVIDER=gemini.")
        from strands.models.gemini import GeminiModel

        return GeminiModel(
            client_args={"api_key": settings.gemini_api_key},
            model_id=settings.gemini_model,
            params={"temperature": 0.4, "max_output_tokens": 220},
        )

    from strands.models.bedrock import BedrockModel

    return BedrockModel(
        model_id=bedrock_model_id or settings.agent_model_id,
        region_name=settings.agent_aws_region,
        temperature=0.4,
        max_tokens=220,
    )


def _agent_safe_negotiation(negotiation: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "currentMonthly",
        "targetMonthly",
        "walkAwayMonthly",
        "provider",
        "liveState",
        "bestOfferMonthly",
        "oneTimeCredit",
        "issueContext",
    }
    return {key: value for key, value in negotiation.items() if key in allowed}


def _decision_summary(decision: dict[str, Any], negotiation: dict[str, Any]) -> dict[str, Any]:
    return {
        "action": decision["action"],
        "objective": decision["objective"],
        "completed": decision["completed"],
        "accepted": decision["accepted"],
        "repIntent": decision["repIntent"],
        "proposedMonthly": decision["proposedMonthly"],
        "credit": decision["credit"],
        "bestOfferMonthly": decision["bestOfferMonthly"],
        "bestCredit": decision["bestCredit"],
        "finalMonthly": decision["finalMonthly"],
        "nextState": decision["nextState"],
        "currentMonthly": negotiation.get("currentMonthly"),
        "targetMonthly": negotiation.get("targetMonthly"),
        "walkAwayMonthly": negotiation.get("walkAwayMonthly"),
        "provider": negotiation.get("provider", "the carrier"),
        "issueContext": negotiation.get("issueContext"),
    }


def _fallback_phrase(decision: dict[str, Any], negotiation: dict[str, Any]) -> str:
    issue_context = negotiation.get("issueContext")
    if issue_context and issue_context.get("taskType") != "telecom_negotiation":
        return phrase_support_action(decision["action"], issue_context)
    return phrase_live_action(
        decision["action"],
        negotiation,
        decision.get("proposedMonthly"),
        decision.get("bestOfferMonthly"),
        float(decision.get("bestCredit") or 0),
    )


def _clean_spoken_text(value: str) -> str:
    text = " ".join(str(value or "").split())
    return text[:700]


def _clean_agent_result_text(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"Tool #\d+:.*?(?=(?:Tool #\d+:)|$)", "", text, flags=re.DOTALL)
    text = re.sub(r"^['\"]|['\"]$", "", text.strip())
    return _clean_spoken_text(text)


def _unauthorized_money_values(text: str, decision: dict[str, Any], negotiation: dict[str, Any]) -> list[str]:
    issue_context = negotiation.get("issueContext")
    if issue_context and issue_context.get("taskType") != "telecom_negotiation":
        return []

    allowed_values = {
        _money_key(negotiation.get("currentMonthly")),
        _money_key(negotiation.get("targetMonthly")),
        _money_key(negotiation.get("walkAwayMonthly")),
        _money_key(decision.get("proposedMonthly")),
        _money_key(decision.get("bestOfferMonthly")),
        _money_key(decision.get("bestCredit")),
        _money_key(decision.get("credit")),
        _money_key(decision.get("finalMonthly")),
    }
    allowed_values.discard(None)

    unauthorized = []
    seen = set()
    for raw in re.findall(
        r"(?:\$|\b)(\d+(?:\.\d{1,2})?)\s*(?:dollars?|per month|a month|/mo|monthly)",
        text.lower(),
    ):
        normalized = _money_key(raw)
        if normalized not in allowed_values and raw not in seen:
            seen.add(raw)
            unauthorized.append(raw)
    return unauthorized


def _money_key(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return None
