from __future__ import annotations

import re
from typing import Any


NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}


def parse_offer_values(text: str, current_monthly: float) -> tuple[float | None, float | None]:
    normalized = _normalize_number_words(text.lower())
    monthly = _parse_monthly_offer(normalized)
    credit = _parse_credit(normalized)
    discount = _parse_discount(normalized)

    if monthly is None and discount is not None:
        monthly = round(max(float(current_monthly) - discount, 0), 2)

    return monthly, credit


def classify_rep_utterance(text: str, negotiation: dict[str, Any]) -> str:
    if _is_support_case(negotiation):
        return classify_support_utterance(text, negotiation)

    normalized = _normalize_number_words(text.lower())
    monthly, credit = parse_offer_values(normalized, float(negotiation["currentMonthly"]))
    target = float(negotiation["targetMonthly"])
    walkaway = float(negotiation["walkAwayMonthly"])

    if _has_any(normalized, ["bye", "goodbye", "that is all", "call is done", "confirmed"]):
        return "close"
    if monthly is not None:
        return "final_discount_offer" if monthly <= max(target, walkaway) else "small_discount_offer"
    if credit is not None:
        return "credit_offer"
    if _has_any(normalized, ["retention", "loyalty", "supervisor", "approval", "escalat"]):
        return "retention_escalation"
    if _has_any(normalized, ["no discount", "no promotions", "not see any promotions", "don't see any promotions", "not available", "cannot", "can't", "standard rate", "nothing available"]):
        return "refusal"
    if _has_any(normalized, ["maybe", "check", "might", "possible", "let me see"]):
        return "soft_refusal"
    if re.search(r"\b(hello|hi)\b|thanks for calling|how can i help", normalized):
        return "greeting"
    return "ambiguous"


def classify_support_utterance(text: str, negotiation: dict[str, Any]) -> str:
    normalized = _normalize_number_words(text.lower())
    issue_context = negotiation.get("issueContext") or {}
    success_signals = [signal.lower() for signal in issue_context.get("successSignals", [])]

    if _has_any(normalized, ["bye", "goodbye", "that is all", "call is done"]):
        return "close"
    if _has_any(normalized, success_signals) and _has_any(normalized, ["processed", "completed", "done", "confirmed", "resolved", "issued", "applied", "updated", "changed", "rebooked", "refunded", "waived", "removed"]):
        return "resolved_confirmation"
    if _has_any(normalized, ["need", "provide", "verify", "booking", "reference", "account", "email", "phone", "address", "date of birth", "receipt"]):
        return "needs_information"
    if _has_any(normalized, ["supervisor", "specialist", "escalat", "manager", "resolution team"]):
        return "escalation"
    if _has_any(normalized, ["cannot", "can't", "not able", "not eligible", "no refund", "policy does not", "nothing i can do"]):
        return "refusal"
    if _has_any(normalized, ["check", "review", "case", "ticket", "wait", "pending", "investigate", "can refund", "can rebook", "can process"]):
        return "pending_review"
    if re.search(r"\b(hello|hi)\b|thanks for calling|how can i help", normalized):
        return "greeting"
    return "ambiguous"


def initial_live_state() -> dict[str, Any]:
    return {"node": "open", "counterCount": 0, "accepted": False, "awaitingProof": False, "closing": False}


def opening_live_turn(negotiation: dict[str, Any]) -> dict[str, Any]:
    if _is_support_case(negotiation):
        issue_context = negotiation["issueContext"]
        text = (
            f"Hi, I'm calling on behalf of the customer about a support issue with {issue_context['companyName']}. "
            f"The problem is: {issue_context['problemSummary']}. "
            f"What we need today is: {issue_context['desiredOutcome']}."
        )
        return {
            "role": "negotiator",
            "intent": "open_support_case",
            "objective": "Opening support case",
            "text": text,
            "proposedMonthly": None,
            "credit": 0.0,
        }

    text = (
        f"Hi, I'm calling about this {negotiation['provider']} bill at ${float(negotiation['currentMonthly']):.2f} a month. "
        f"Can you check loyalty or retention pricing closer to ${float(negotiation['targetMonthly']):.2f}?"
    )
    return {
        "role": "negotiator",
        "intent": "open_with_bill_facts",
        "objective": "Opening with bill facts",
        "text": text,
        "proposedMonthly": None,
        "credit": 0.0,
    }


def advance_live_policy(negotiation: dict[str, Any], rep_text: str) -> dict[str, Any]:
    if _is_support_case(negotiation):
        return advance_support_policy(negotiation, rep_text)

    state = dict(negotiation.get("liveState") or initial_live_state())
    rep_intent = classify_rep_utterance(rep_text, negotiation)
    proposed_monthly, credit = parse_offer_values(rep_text, float(negotiation["currentMonthly"]))
    target = float(negotiation["targetMonthly"])
    walkaway = float(negotiation["walkAwayMonthly"])
    current = float(negotiation["currentMonthly"])
    best_offer = _best_offer(negotiation.get("bestOfferMonthly"), proposed_monthly)
    best_credit = max(float(negotiation.get("oneTimeCredit") or 0), float(credit or 0))

    completed = False
    accepted = False

    awaiting_proof = bool(state.get("awaitingProof"))

    if awaiting_proof and rep_intent == "close":
        action = "confirm_accepted_offer"
        next_node = "confirmed"
        completed = True
        accepted = True
    elif proposed_monthly is not None and proposed_monthly <= max(target, walkaway):
        action = "accept_offer"
        next_node = "awaiting_confirmation"
        accepted = True
    elif rep_intent == "credit_offer":
        action = "ask_for_credit_plus_rate_relief"
        next_node = "credit_only_seen"
    elif rep_intent in {"small_discount_offer", "retention_escalation"}:
        action = "counter_to_target"
        next_node = "countering"
    elif state.get("counterCount", 0) >= 2 and rep_intent in {"refusal", "soft_refusal", "ambiguous"}:
        action = "exit_without_accepting"
        next_node = "walkaway_reached"
        completed = True
    elif rep_intent in {"refusal", "soft_refusal", "ambiguous", "greeting"}:
        action = "push_for_retention"
        next_node = "rep_refusal"
    elif rep_intent == "close":
        action = "accept_offer" if best_offer and best_offer <= max(target, walkaway) else "exit_without_accepting"
        next_node = "awaiting_confirmation" if action == "accept_offer" else "walkaway_reached"
        completed = action != "accept_offer"
        accepted = action == "accept_offer"
    else:
        action = "push_for_retention"
        next_node = "rep_refusal"

    counter_count = int(state.get("counterCount", 0)) + (1 if action == "counter_to_target" else 0)
    next_state = {
        "node": next_node,
        "counterCount": counter_count,
        "accepted": accepted,
        "awaitingProof": action == "accept_offer" and not completed,
        "closing": completed,
    }
    ai_text = phrase_live_action(action, negotiation, proposed_monthly, best_offer, best_credit)

    return {
        "repIntent": rep_intent,
        "action": action,
        "nextState": next_state,
        "text": ai_text,
        "objective": _objective_for_action(action),
        "proposedMonthly": proposed_monthly,
        "credit": credit,
        "bestOfferMonthly": best_offer,
        "bestCredit": best_credit,
        "completed": completed,
        "accepted": accepted,
        "finalMonthly": best_offer if accepted and best_offer is not None else current,
    }


def advance_support_policy(negotiation: dict[str, Any], rep_text: str) -> dict[str, Any]:
    state = dict(negotiation.get("liveState") or initial_live_state())
    rep_intent = classify_support_utterance(rep_text, negotiation)
    issue_context = negotiation["issueContext"]
    turn_count = int(state.get("counterCount", 0))
    completed = False
    accepted = False

    if rep_intent == "resolved_confirmation":
        action = "confirm_task_complete"
        next_node = "resolved"
        completed = True
        accepted = True
    elif rep_intent == "needs_information":
        action = "provide_available_context"
        next_node = "context_requested"
    elif rep_intent in {"refusal", "close"} and turn_count >= 2:
        action = "escalate_or_capture_next_step"
        next_node = "unresolved_next_step"
        completed = True
    elif rep_intent in {"refusal", "escalation"}:
        action = "ask_for_escalation"
        next_node = "escalating"
    elif rep_intent in {"pending_review", "ambiguous"}:
        action = "ask_for_concrete_next_step"
        next_node = "pending_review"
    else:
        action = "explain_support_goal"
        next_node = "explaining_goal"

    next_state = {
        "node": next_node,
        "counterCount": turn_count + 1,
        "accepted": accepted,
        "closing": completed,
    }
    text = phrase_support_action(action, issue_context)
    return {
        "repIntent": rep_intent,
        "action": action,
        "nextState": next_state,
        "text": text,
        "objective": _support_objective_for_action(action),
        "proposedMonthly": None,
        "credit": None,
        "bestOfferMonthly": negotiation.get("bestOfferMonthly"),
        "bestCredit": float(negotiation.get("oneTimeCredit") or 0),
        "completed": completed,
        "accepted": accepted,
        "finalMonthly": float(negotiation.get("currentMonthly") or 0),
    }


def phrase_support_action(action: str, issue_context: dict[str, Any]) -> str:
    company = issue_context["companyName"]
    desired = issue_context["desiredOutcome"]
    facts = issue_context.get("customerFacts", [])
    criteria = issue_context.get("completionCriteria", [])
    primary_criterion = criteria[0] if criteria else desired
    escalation = ", ".join(issue_context.get("escalationTerms", ["supervisor"])[:2])

    lines = {
        "explain_support_goal": (
            f"I'm trying to get this resolved while we're on the line. "
            f"The issue is {issue_context['problemSummary']}, and the customer needs {desired}."
        ),
        "provide_available_context": (
            ("I have these details ready: " + "; ".join(facts[:4]) + ". " if facts else "I can provide the account, booking, receipt, or identity details you need. ")
            + "Tell me the specific detail you need and I'll keep this moving."
        ),
        "ask_for_escalation": (
            f"If this is outside your access, please transfer me to {escalation}. "
            f"I need a real path to get this done: {desired}."
        ),
        "ask_for_concrete_next_step": (
            f"That sounds promising. Before we move on, what exactly happens next, who owns it, and when will it show up? "
            f"What I need confirmed is: {primary_criterion}."
        ),
        "confirm_task_complete": (
            f"Perfect, thank you. Just to close the loop, please confirm this is complete: {primary_criterion}. "
            "If there is a case number or timeline, please give me that for the customer's records."
        ),
        "escalate_or_capture_next_step": (
            f"I don't want to end the call without a clear resolution path. Please create a case with a reference number, "
            f"or transfer me to {escalation}."
        ),
    }
    return lines[action]


def phrase_live_action(
    action: str,
    negotiation: dict[str, Any],
    proposed_monthly: float | None,
    best_offer: float | None,
    credit: float,
) -> str:
    target = float(negotiation["targetMonthly"])
    walkaway = float(negotiation["walkAwayMonthly"])
    current = float(negotiation["currentMonthly"])

    lines = {
        "push_for_retention": (
            f"I understand. Can you check loyalty or retention pricing? "
            f"${current:.2f} a month is too high for this plan."
        ),
        "counter_to_target": (
            f"That's better, but it still leaves the bill high. If you can do ${target:.2f} a month, "
            "we can settle it on this call."
        ),
        "ask_for_credit_plus_rate_relief": (
            f"I appreciate the credit. The monthly charge is still the real issue. "
            f"Can you also bring the plan closer to ${target:.2f} a month?"
        ),
        "accept_offer": (
            f"That works. Please apply ${best_offer or proposed_monthly or walkaway:.2f} a month"
            + (f" and the ${credit:.2f} credit" if credit else "")
            + " now. Before we end, please confirm the effective date and that the account notes show this change."
        ),
        "confirm_accepted_offer": (
            "Perfect. Please keep that confirmation in the account notes. That resolves what I called about."
        ),
        "exit_without_accepting": (
            f"I can't accept anything above ${walkaway:.2f}. Please note that we called for retention pricing, "
            "and the customer will compare alternatives."
        ),
    }
    return lines[action]


def live_result_summary(negotiation: dict[str, Any], final_monthly: float, credit: float) -> dict[str, Any]:
    if _is_support_case(negotiation):
        return live_support_result_summary(negotiation, resolved=bool((negotiation.get("liveState") or {}).get("accepted")))

    current = round(float(negotiation["currentMonthly"]), 2)
    final = round(max(float(final_monthly), 0), 2)
    monthly_savings = round(max(current - final, 0), 2)
    annual_savings = round(monthly_savings * 12, 2)
    credit = round(max(float(credit), 0), 2)
    return {
        "currentMonthly": current,
        "newMonthly": final,
        "monthlySavings": monthly_savings,
        "annualSavings": annual_savings,
        "oneTimeCredit": credit,
        "effectiveFirstYearValue": round(annual_savings + credit, 2),
        "summary": f"RateDrop reduced the bill from ${current:.2f} to ${final:.2f} per month.",
        "transcriptSummary": [
            f"Opened on {negotiation['provider']} billing pressure at ${current:.2f}/month.",
            f"Live rep speech was classified into controlled negotiation intents.",
            f"Backend policy accepted ${final:.2f}/month because it met the walk-away threshold.",
            f"Final value includes a ${credit:.2f} one-time credit." if credit else "Final value did not depend on a one-time credit.",
        ],
    }


def live_support_result_summary(negotiation: dict[str, Any], resolved: bool) -> dict[str, Any]:
    issue_context = negotiation["issueContext"]
    company = issue_context["companyName"]
    status = "completed" if resolved else "advanced"
    criteria = issue_context.get("completionCriteria", [])
    return {
        "currentMonthly": 0.0,
        "newMonthly": 0.0,
        "monthlySavings": 0.0,
        "annualSavings": 0.0,
        "oneTimeCredit": 0.0,
        "effectiveFirstYearValue": 0.0,
        "summary": f"RateDrop {status} the {company} support request.",
        "transcriptSummary": [
            f"Opened a {issue_context['taskType'].replace('_', ' ')} case with {company}.",
            f"Problem: {issue_context['problemSummary']}.",
            f"Desired outcome: {issue_context['desiredOutcome']}.",
            f"Completion criteria checked: {criteria[0] if criteria else issue_context['desiredOutcome']}.",
        ],
    }


def _parse_monthly_offer(text: str) -> float | None:
    patterns = [
        r"(?:to|at|for|do|approve|get approval for)\s+\$?(\d+(?:\.\d{1,2})?)\s*(?:dollars?)?\s*(?:a|per)?\s*(?:month|monthly|/mo)",
        r"\$?(\d+(?:\.\d{1,2})?)\s*(?:dollars?)?\s*(?:a|per)?\s*(?:month|monthly|/mo)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return round(float(match.group(1)), 2)
    return None


def _parse_credit(text: str) -> float | None:
    match = re.search(r"\$?(\d+(?:\.\d{1,2})?)\s*(?:dollars?)?\s*(?:one[- ]time\s*)?(?:credit|adjustment)", text)
    return round(float(match.group(1)), 2) if match else None


def _parse_discount(text: str) -> float | None:
    match = re.search(r"\$?(\d+(?:\.\d{1,2})?)\s*(?:dollars?)?\s*(?:off|discount|reduction)", text)
    return round(float(match.group(1)), 2) if match else None


def _normalize_number_words(text: str) -> str:
    normalized = text.replace("-", " ")
    for phrase in sorted(_compound_number_phrases(), key=len, reverse=True):
        normalized = re.sub(rf"\b{re.escape(phrase)}\b", str(_compound_number_phrases()[phrase]), normalized)
    for word, value in NUMBER_WORDS.items():
        normalized = re.sub(rf"\b{word}\b", str(value), normalized)
    return normalized


def _compound_number_phrases() -> dict[str, int]:
    phrases: dict[str, int] = {}
    tens = {word: value for word, value in NUMBER_WORDS.items() if value >= 20 and value % 10 == 0}
    ones = {word: value for word, value in NUMBER_WORDS.items() if 1 <= value <= 9}
    for ten_word, ten_value in tens.items():
        for one_word, one_value in ones.items():
            phrases[f"{ten_word} {one_word}"] = ten_value + one_value
    return phrases


def _best_offer(existing: Any, proposed: float | None) -> float | None:
    if proposed is None:
        return float(existing) if existing is not None else None
    if existing is None:
        return proposed
    return min(float(existing), proposed)


def _objective_for_action(action: str) -> str:
    return {
        "push_for_retention": "Pushing for retention review",
        "counter_to_target": "Countering toward target monthly rate",
        "ask_for_credit_plus_rate_relief": "Requesting monthly relief in addition to credit",
        "accept_offer": "Accepting offer and requesting proof",
        "confirm_accepted_offer": "Confirming accepted offer proof",
        "exit_without_accepting": "Exiting because offer missed walk-away threshold",
    }[action]


def _support_objective_for_action(action: str) -> str:
    return {
        "explain_support_goal": "Explaining requested support outcome",
        "provide_available_context": "Providing available case context",
        "ask_for_escalation": "Requesting escalation path",
        "ask_for_concrete_next_step": "Getting owner, action, and timeline",
        "confirm_task_complete": "Confirming support task completion",
        "escalate_or_capture_next_step": "Capturing unresolved next step",
    }[action]


def _has_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def _is_support_case(negotiation: dict[str, Any]) -> bool:
    issue_context = negotiation.get("issueContext")
    return bool(issue_context and issue_context.get("taskType") != "telecom_negotiation")
