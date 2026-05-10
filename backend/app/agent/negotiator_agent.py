from __future__ import annotations

import json
import logging
import os
import re
import asyncio
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
    "confirm_accepted_offer",
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
    settings = get_settings()
    if settings.normalized_agent_mode == "adk":
        return _run_google_adk_negotiator_agent(negotiation, rep_text)
    return advance_live_policy(negotiation, rep_text)


def _run_google_adk_negotiator_agent(negotiation: dict[str, Any], rep_text: str) -> dict[str, Any]:
    """
    Run the Google Agent Development Kit agent around RateDrop's
    deterministic policy tool. ADK handles phrasing; policy owns decisions.
    """
    pending_decision: dict[str, Any] = {}
    settings = get_settings()

    if not settings.gemini_api_key:
        logger.warning("Google ADK agent unavailable; GEMINI_API_KEY is missing.")
        return advance_live_policy(negotiation, rep_text)

    try:
        from google.adk.agents import Agent
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai import types
    except Exception as error:
        logger.warning("Google ADK unavailable; using deterministic live policy: %s", error)
        return advance_live_policy(negotiation, rep_text)

    def analyze_rep_speech(rep_text: str, negotiation_json: str) -> dict[str, Any]:
        """
        Run RateDrop's deterministic policy engine against the rep speech.
        Call this first on every turn.
        """
        negotiation_payload = json.loads(negotiation_json)
        decision = advance_live_policy(negotiation_payload, rep_text)
        pending_decision.clear()
        pending_decision.update(decision)
        return _decision_summary(decision, negotiation_payload)

    def finalize_response(action: str, spoken_text: str, completed: bool) -> dict[str, Any]:
        """
        Validate and register the final spoken response for the policy action.
        Call this as the last tool before ending.
        """
        if action not in ALLOWED_ACTIONS:
            return {"status": "error", "error": f"unknown action '{action}'"}
        if pending_decision and action != pending_decision.get("action"):
            return {"status": "error", "error": f"action must remain {pending_decision.get('action')}"}
        clean_text = _clean_spoken_text(spoken_text)
        if not clean_text:
            return {"status": "error", "error": "spoken_text must not be empty"}
        unauthorized_money = _unauthorized_money_values(clean_text, pending_decision, negotiation)
        if unauthorized_money:
            return {"status": "error", "error": f"unauthorized monetary value(s): {', '.join(unauthorized_money)}"}
        pending_decision["_agent_text"] = clean_text
        pending_decision["_agent_completed"] = bool(completed)
        return {"status": "approved"}

    try:
        if not os.environ.get("GOOGLE_API_KEY"):
            os.environ["GOOGLE_API_KEY"] = settings.gemini_api_key
        final_text = _run_async_blocking(
            _run_google_adk_turn_async(
                Agent=Agent,
                Runner=Runner,
                InMemorySessionService=InMemorySessionService,
                types=types,
                tools=[analyze_rep_speech, finalize_response],
                rep_text=rep_text,
                negotiation=negotiation,
            )
        )
    except Exception as error:
        logger.warning("Google ADK agent turn failed; using deterministic live policy: %s", error)
        return advance_live_policy(negotiation, rep_text)

    if not pending_decision:
        logger.warning("Google ADK agent did not call analyze_rep_speech; using deterministic live policy.")
        return advance_live_policy(negotiation, rep_text)

    decision = dict(pending_decision)
    agent_text = decision.pop("_agent_text", None)
    decision.pop("_agent_completed", None)
    result_text = _clean_agent_result_text(final_text) if not agent_text else None
    if result_text and _unauthorized_money_values(result_text, decision, negotiation):
        result_text = None
    decision["text"] = agent_text or result_text or _fallback_phrase(decision, negotiation)
    return decision


async def _run_google_adk_turn_async(
    *,
    Agent: Any,
    Runner: Any,
    InMemorySessionService: Any,
    types: Any,
    tools: list[Any],
    rep_text: str,
    negotiation: dict[str, Any],
) -> str:
    settings = get_settings()
    app_name = "ratedrop_phone_agent"
    user_id = "phone-call"
    session_id = f"negotiation-{str(negotiation.get('_id', 'local'))}"
    agent = Agent(
        model=settings.gemini_model,
        name="ratedrop_policy_bound_phone_agent",
        instruction=SYSTEM_PROMPT,
        tools=tools,
    )
    session_service = InMemorySessionService()
    await session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)
    runner = Runner(agent=agent, app_name=app_name, session_service=session_service)
    message = types.Content(
        role="user",
        parts=[
            types.Part(
                text=(
                    "The representative just said: "
                    f"{json.dumps(rep_text)}\n\n"
                    f"Negotiation state: {json.dumps(_agent_safe_negotiation(negotiation), default=str)}"
                )
            )
        ],
    )

    final_response = ""
    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=message):
        if event.is_final_response() and event.content and event.content.parts:
            final_response = " ".join(part.text or "" for part in event.content.parts).strip()
    return final_response


def _run_async_blocking(coro: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    # This path is defensive. The production caller already runs this function
    # in a worker thread, but tests or future routes may call it from a loop.
    import threading

    result: dict[str, Any] = {}

    def runner() -> None:
        try:
            result["value"] = asyncio.run(coro)
        except Exception as error:
            result["error"] = error

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join()
    if "error" in result:
        raise result["error"]
    return result.get("value")


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

    allowed_values = _allowed_money_values_for_action(decision, negotiation)
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


def _allowed_money_values_for_action(decision: dict[str, Any], negotiation: dict[str, Any]) -> set[str | None]:
    current = _money_key(negotiation.get("currentMonthly"))
    target = _money_key(negotiation.get("targetMonthly"))
    walkaway = _money_key(negotiation.get("walkAwayMonthly"))
    proposed = _money_key(decision.get("proposedMonthly"))
    best_offer = _money_key(decision.get("bestOfferMonthly"))
    credit = _money_key(decision.get("credit"))
    best_credit = _money_key(decision.get("bestCredit"))
    final = _money_key(decision.get("finalMonthly"))

    action = str(decision.get("action") or "")
    if action == "counter_to_target":
        return {current, target, proposed, best_offer}
    if action == "ask_for_credit_plus_rate_relief":
        return {current, target, credit, best_credit}
    if action == "accept_offer":
        return {proposed, best_offer, credit, best_credit, final}
    if action == "exit_without_accepting":
        return {current, walkaway, best_offer, proposed}
    if action == "push_for_retention":
        return {current, target}
    return {current, target, walkaway, proposed, best_offer, credit, best_credit, final}
