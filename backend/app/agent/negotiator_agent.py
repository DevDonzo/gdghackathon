from __future__ import annotations

import json
import logging
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
""".strip()


def run_negotiator_agent(negotiation: dict[str, Any], rep_text: str) -> dict[str, Any]:
    """
    Return the same decision shape as advance_live_policy(), with optional
    agent-generated spoken text. Any agent/tool failure falls back to the
    deterministic policy and phrase generator.
    """
    settings = get_settings()
    if not settings.gemini_api_key:
        return advance_live_policy(negotiation, rep_text)

    pending_decision: dict[str, Any] = {}

    try:
        from strands import Agent, tool
        from strands.models.gemini import GeminiModel
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
        pending_decision["_agent_text"] = clean_text
        pending_decision["_agent_completed"] = bool(completed)
        return "approved"

    try:
        model = GeminiModel(
            client_args={"api_key": settings.gemini_api_key},
            model_id=settings.gemini_model,
            params={"temperature": 0.4, "max_output_tokens": 220},
        )
        agent = Agent(
            model=model,
            tools=[analyze_rep_speech, finalize_response],
            system_prompt=SYSTEM_PROMPT,
        )
        agent(
            "The representative just said: "
            f"{json.dumps(rep_text)}\n\n"
            f"Negotiation state: {json.dumps(_agent_safe_negotiation(negotiation), default=str)}"
        )
    except Exception as error:
        logger.warning("Strands agent turn failed; using deterministic live policy: %s", error)
        return advance_live_policy(negotiation, rep_text)

    if not pending_decision:
        logger.warning("Strands agent did not call analyze_rep_speech; using deterministic live policy.")
        return advance_live_policy(negotiation, rep_text)

    decision = dict(pending_decision)
    agent_text = decision.pop("_agent_text", None)
    decision.pop("_agent_completed", None)
    decision["text"] = agent_text or _fallback_phrase(decision, negotiation)
    return decision


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
