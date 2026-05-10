from __future__ import annotations

from typing import Any


TASK_TYPES = {
    "telecom_negotiation",
    "billing_dispute",
    "travel_support",
    "account_support",
    "generic_support",
}


def build_issue_context(bill: dict[str, Any], payload: Any | None = None) -> dict[str, Any]:
    issue = _clean(getattr(payload, "issueDescription", None) if payload else None)
    desired = _clean(getattr(payload, "desiredOutcome", None) if payload else None)
    company = _clean(getattr(payload, "companyName", None) if payload else None) or bill.get("provider") or "service provider"
    customer_facts = _clean_list(getattr(payload, "customerFacts", []) if payload else [])
    constraints = _clean_list(getattr(payload, "constraints", []) if payload else [])
    requested_criteria = _clean_list(getattr(payload, "completionCriteria", []) if payload else [])

    if not issue:
        issue = _default_issue(bill)
    if not desired:
        desired = _default_outcome(bill, issue)

    task_type = _classify_task(company, issue, desired, bill)
    completion_criteria = requested_criteria or _default_completion_criteria(task_type, desired)
    success_signals = _success_signals(task_type)

    return {
        "companyName": company[:80],
        "taskType": task_type,
        "problemSummary": _trim_sentence(issue[:320]),
        "desiredOutcome": _trim_sentence(desired[:240]),
        "customerFacts": customer_facts[:8],
        "constraints": constraints[:6],
        "completionCriteria": completion_criteria[:6],
        "successSignals": success_signals,
        "escalationTerms": _escalation_terms(task_type),
    }


def is_telecom_context(issue_context: dict[str, Any] | None) -> bool:
    if not issue_context:
        return True
    return issue_context.get("taskType") == "telecom_negotiation"


def _classify_task(company: str, issue: str, desired: str, bill: dict[str, Any]) -> str:
    text = f"{company} {issue} {desired} {bill.get('planName', '')}".lower()
    provider = str(bill.get("provider", "")).lower()
    telecom_provider = provider in {"bell", "rogers", "telus"} or company.lower() in {"bell", "rogers", "telus"}
    rate_or_retention_goal = any(token in text for token in ["rate", "bill", "monthly", "plan", "promo", "retention", "loyalty", "lower"])
    explicit_dispute = any(token in text for token in ["dispute", "wrong charge", "incorrect charge", "unauthorized charge", "refund"])
    if telecom_provider and (rate_or_retention_goal or not explicit_dispute):
        return "telecom_negotiation"
    if any(token in text for token in ["flight", "airline", "air canada", "booking", "baggage", "ticket", "refund"]):
        return "travel_support"
    if any(token in text for token in ["charge", "charged", "fee", "refund", "credit", "invoice", "receipt", "dispute"]):
        return "billing_dispute"
    if any(token in text for token in ["password", "login", "account", "subscription", "cancel", "address", "profile"]):
        return "account_support"
    if telecom_provider and any(token in text for token in ["rate", "bill", "plan", "promo", "retention"]):
        return "telecom_negotiation"
    return "generic_support"


def _default_issue(bill: dict[str, Any]) -> str:
    angles = bill.get("negotiationAngles", [])
    if angles:
        return angles[0]
    return f"Review the {bill.get('provider', 'provider')} account and resolve the billing issue."


def _default_outcome(bill: dict[str, Any], issue: str) -> str:
    provider = bill.get("provider", "provider")
    if str(provider).lower() in {"bell", "rogers", "telus"}:
        return "Reduce the recurring bill or secure a meaningful credit."
    return f"Resolve the issue: {issue}."


def _default_completion_criteria(task_type: str, desired: str) -> list[str]:
    if task_type == "telecom_negotiation":
        return ["Carrier confirms the new monthly rate or credit.", "Carrier confirms when the change appears on the account."]
    if task_type == "billing_dispute":
        return ["Representative confirms the disputed charge was removed, refunded, or credited.", "Representative gives timing for the adjustment."]
    if task_type == "travel_support":
        return ["Representative confirms the refund, rebooking, baggage fix, or travel-case action.", "Representative gives a confirmation number or next-step timeline."]
    if task_type == "account_support":
        return ["Representative confirms the requested account change is complete.", "Representative confirms any follow-up action or reference number."]
    return [f"Representative confirms this outcome: {desired}.", "Representative gives a confirmation, reference number, or timeline."]


def _success_signals(task_type: str) -> list[str]:
    common = ["confirmed", "completed", "processed", "done", "resolved", "reference number", "case number"]
    if task_type == "travel_support":
        return [*common, "refund", "rebooked", "travel credit", "ticket", "booking"]
    if task_type == "billing_dispute":
        return [*common, "credited", "refunded", "removed", "waived", "adjustment"]
    if task_type == "account_support":
        return [*common, "updated", "changed", "cancelled", "restored"]
    return common


def _escalation_terms(task_type: str) -> list[str]:
    if task_type == "travel_support":
        return ["supervisor", "resolution desk", "customer relations", "refund department"]
    if task_type == "billing_dispute":
        return ["billing supervisor", "adjustments team", "customer care"]
    if task_type == "account_support":
        return ["account specialist", "supervisor", "technical support"]
    return ["supervisor", "specialist", "resolution team"]


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _trim_sentence(value: str) -> str:
    return value.strip().rstrip(".")


def _clean_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [_clean(value)[:180] for value in values if _clean(value)]
