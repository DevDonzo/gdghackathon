from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from google import genai

from backend.app.core.config import get_settings
from backend.app.db.mongo import get_collections
from backend.app.models.schemas import object_id, serialize_negotiation, serialize_turn
from backend.app.services.events import publish
from backend.app.services.issue_context import is_telecom_context


active_runs: dict[str, asyncio.Task[None]] = {}


@dataclass(slots=True)
class Scenario:
    scenario_id: str
    label: str
    objective_labels: list[str]


@dataclass(frozen=True, slots=True)
class MarketProfile:
    benchmark_monthly: float
    retention_floor: float
    first_offer_spread: float
    loyalty_credit: float


MARKET_PROFILES = {
    "bell": MarketProfile(benchmark_monthly=58.0, retention_floor=52.0, first_offer_spread=16.0, loyalty_credit=25.0),
    "rogers": MarketProfile(benchmark_monthly=78.0, retention_floor=73.5, first_offer_spread=10.0, loyalty_credit=0.0),
    "telus": MarketProfile(benchmark_monthly=66.0, retention_floor=65.0, first_offer_spread=6.0, loyalty_credit=20.0),
}


SCENARIOS = {
    "happy_path": Scenario(
        scenario_id="happy_path",
        label="Retention win",
        objective_labels=[
            "Opening with bill facts",
            "Holding the line against the first refusal",
            "Requesting retention options",
            "Countering toward the target rate",
            "Locking the new monthly rate",
        ],
    ),
    "escalation_path": Scenario(
        scenario_id="escalation_path",
        label="Escalation required",
        objective_labels=[
            "Explaining the billing pain point",
            "Asking for loyalty review",
            "Pushing for retention escalation",
            "Evaluating a smaller offer",
            "Accepting the best available rate",
        ],
    ),
    "fee_recovery_path": Scenario(
        scenario_id="fee_recovery_path",
        label="Fee recovery",
        objective_labels=[
            "Questioning fee-based charges",
            "Requesting a goodwill credit",
            "Asking for plan relief on top",
            "Securing the credit and revised total",
            "Confirming the adjusted bill",
        ],
    ),
}


NEGOTIATOR_SCHEMA = {
    "type": "object",
    "properties": {
        "turns": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"say": {"type": "string"}},
                "required": ["say"],
            },
        }
    },
    "required": ["turns"],
}


def _determine_scenario(bill: dict[str, Any]) -> Scenario:
    preferred = bill.get("preferredScenarioId")
    if preferred in SCENARIOS:
        return SCENARIOS[preferred]
    line_items = bill.get("lineItems", [])
    angles = " ".join(bill.get("negotiationAngles", []) + bill.get("redFlags", [])).lower()
    if any(item.get("category") in {"fee", "overage"} and float(item.get("amount", 0)) > 0 for item in line_items):
        return SCENARIOS["fee_recovery_path"]
    if "promo" in angles or bill.get("monthlyTotal", 0) >= 80:
        return SCENARIOS["happy_path"]
    return SCENARIOS["escalation_path"]


def _round_money(value: float) -> float:
    return round(max(value, 0.0) + 1e-9, 2)


def _provider_profile(provider: str, current: float) -> MarketProfile:
    provider_key = provider.lower()
    for key, profile in MARKET_PROFILES.items():
        if key in provider_key:
            return profile
    benchmark = _round_money(max(45.0, min(current * 0.86, current - 8.0)))
    return MarketProfile(
        benchmark_monthly=benchmark,
        retention_floor=_round_money(max(40.0, benchmark - 6.0)),
        first_offer_spread=8.0,
        loyalty_credit=0.0,
    )


def _bill_pressure(bill: dict[str, Any]) -> dict[str, float | bool]:
    line_items = bill.get("lineItems", [])
    fee_total = sum(
        float(item.get("amount", 0))
        for item in line_items
        if item.get("category") in {"fee", "overage"} and float(item.get("amount", 0)) > 0
    )
    recurring_extra = sum(
        float(item.get("amount", 0))
        for item in line_items
        if item.get("recurring") and item.get("category") in {"fee", "other"} and float(item.get("amount", 0)) > 0
    )
    text = " ".join([*bill.get("negotiationAngles", []), *bill.get("redFlags", []), bill.get("planName", "")]).lower()
    return {
        "fee_total": _round_money(fee_total),
        "recurring_extra": _round_money(recurring_extra),
        "promo_pressure": "promo" in text or "roll" in text,
        "switch_pressure": "competitor" in text or "switch" in text or "market" in text,
    }


def _financials(bill: dict[str, Any], scenario: Scenario) -> dict[str, float]:
    current = float(bill["monthlyTotal"])
    profile = _provider_profile(str(bill.get("provider", "")), current)
    pressure = _bill_pressure(bill)
    fee_credit = float(pressure["fee_total"])
    recurring_extra = float(pressure["recurring_extra"])
    benchmark = min(profile.benchmark_monthly, max(profile.retention_floor, current - 6.0))
    target_anchor = profile.retention_floor

    if pressure["promo_pressure"]:
        target_anchor = min(target_anchor, profile.benchmark_monthly - 4.0)
    if pressure["switch_pressure"]:
        target_anchor = min(target_anchor, profile.benchmark_monthly - 2.0)
    if recurring_extra:
        target_anchor = min(target_anchor, current - min(recurring_extra, 12.0))
    target_anchor = _round_money(max(35.0, min(target_anchor, current - 5.0)))

    if scenario.scenario_id == "happy_path":
        offer_two = target_anchor
        offer_one = _round_money(min(current - 5.0, max(offer_two + profile.first_offer_spread, benchmark + 10.0)))
        walk_away = _round_money(min(current - 4.0, max(offer_two + 8.0, benchmark)))
        credit = profile.loyalty_credit if fee_credit <= 0 else min(40.0, fee_credit + 10.0)
    elif scenario.scenario_id == "fee_recovery_path":
        credit = _round_money(min(max(fee_credit, profile.loyalty_credit, 20.0), 45.0))
        offer_two = _round_money(max(profile.retention_floor, current - min(max(recurring_extra, fee_credit, 8.0), 14.0)))
        offer_one = _round_money(min(current - 3.0, max(offer_two + 4.0, current - 6.0)))
        walk_away = current
    else:
        offer_two = _round_money(max(profile.retention_floor, min(current - 8.0, benchmark - 2.0)))
        offer_one = _round_money(min(current - 4.0, max(offer_two + profile.first_offer_spread * 0.7, benchmark + 2.0)))
        walk_away = _round_money(min(current - 3.0, max(offer_two + 6.0, benchmark)))
        credit = 0.0

    return {
        "current": _round_money(current),
        "offer_one": offer_one,
        "offer_two": offer_two,
        "walk_away": walk_away,
        "credit": credit,
        "market_benchmark": _round_money(profile.benchmark_monthly),
        "fee_pressure": _round_money(fee_credit),
    }


def _plan_blueprints(bill: dict[str, Any], scenario: Scenario) -> tuple[list[dict[str, Any]], dict[str, float]]:
    money = _financials(bill, scenario)
    provider = bill["provider"]
    plan_name = bill["planName"]
    angles = bill.get("negotiationAngles", [])
    primary_angle = angles[0] if angles else "retention options"

    if scenario.scenario_id == "happy_path":
        turns = [
            {"role": "negotiator", "intent": "probe", "objective": scenario.objective_labels[0], "facts": f"Monthly bill is ${money['current']:.2f}. Mention {primary_angle} on the {plan_name}. Comparable target benchmark is around ${money['market_benchmark']:.2f}."},
            {"role": "rep", "intent": "deny", "objective": scenario.objective_labels[1], "facts": f"{provider} rep initially resists and says the current plan is already competitive."},
            {"role": "negotiator", "intent": "request_retention", "objective": scenario.objective_labels[2], "facts": f"Ask for retention options and reference loyalty. Do not invent discounts. Target around ${money['offer_two']:.2f}."},
            {"role": "rep", "intent": "offer_discount", "objective": scenario.objective_labels[3], "facts": f"Offer an interim monthly rate of ${money['offer_one']:.2f}."},
            {"role": "negotiator", "intent": "counter_offer", "objective": scenario.objective_labels[3], "facts": f"Counter politely toward ${money['offer_two']:.2f} and mention switching risk."},
            {"role": "rep", "intent": "retention_offer", "objective": scenario.objective_labels[4], "facts": f"Approve a final rate of ${money['offer_two']:.2f} and a one-time credit of ${money['credit']:.2f}."},
            {"role": "negotiator", "intent": "accept", "objective": scenario.objective_labels[4], "facts": "Accept the offer and confirm the new monthly rate."},
            {"role": "rep", "intent": "close", "objective": scenario.objective_labels[4], "facts": "Confirm the changes are applied and the credit will post on the next bill."},
        ]
    elif scenario.scenario_id == "fee_recovery_path":
        turns = [
            {"role": "negotiator", "intent": "probe", "objective": scenario.objective_labels[0], "facts": f"Question the unexpected fee charges and cite the ${money['current']:.2f} bill. Fee pressure totals about ${money['fee_pressure']:.2f}."},
            {"role": "rep", "intent": "deny", "objective": scenario.objective_labels[1], "facts": f"{provider} rep says the charges are valid unless a goodwill review is approved."},
            {"role": "negotiator", "intent": "push_discount", "objective": scenario.objective_labels[1], "facts": f"Request a goodwill credit and emphasize the disputed fee angle: {primary_angle}."},
            {"role": "rep", "intent": "offer_credit", "objective": scenario.objective_labels[2], "facts": f"Offer a one-time credit of ${money['credit']:.2f}, but keep the monthly plan unchanged for now."},
            {"role": "negotiator", "intent": "counter_offer", "objective": scenario.objective_labels[2], "facts": f"Ask whether the monthly bill can also come down to ${money['offer_two']:.2f}."},
            {"role": "rep", "intent": "retention_offer", "objective": scenario.objective_labels[3], "facts": f"Approve a reduced monthly rate of ${money['offer_two']:.2f} while keeping the ${money['credit']:.2f} credit."},
            {"role": "negotiator", "intent": "accept", "objective": scenario.objective_labels[4], "facts": "Accept both the lower rate and the credit."},
            {"role": "rep", "intent": "close", "objective": scenario.objective_labels[4], "facts": "Confirm the credit and reduced monthly total are now attached to the account."},
        ]
    else:
        turns = [
            {"role": "negotiator", "intent": "probe", "objective": scenario.objective_labels[0], "facts": f"Open with the ${money['current']:.2f} monthly total and explain the plan is no longer competitive against a ${money['market_benchmark']:.2f} benchmark."},
            {"role": "rep", "intent": "deny", "objective": scenario.objective_labels[1], "facts": f"{provider} rep says there are no automatic promotions available."},
            {"role": "negotiator", "intent": "request_retention", "objective": scenario.objective_labels[2], "facts": "Ask for a loyalty review or retention department."},
            {"role": "rep", "intent": "offer_discount", "objective": scenario.objective_labels[3], "facts": f"Offer a smaller monthly rate of ${money['offer_one']:.2f} after escalation."},
            {"role": "negotiator", "intent": "counter_offer", "objective": scenario.objective_labels[3], "facts": f"Push once toward ${money['offer_two']:.2f} without being aggressive."},
            {"role": "rep", "intent": "retention_offer", "objective": scenario.objective_labels[4], "facts": f"Settle at ${money['offer_two']:.2f} with no additional credit."},
            {"role": "negotiator", "intent": "accept", "objective": scenario.objective_labels[4], "facts": "Accept the final monthly rate."},
            {"role": "rep", "intent": "close", "objective": scenario.objective_labels[4], "facts": "Confirm the new plan takes effect immediately."},
        ]

    return turns, money


def _fallback_line(turn: dict[str, Any], bill: dict[str, Any], money: dict[str, float]) -> str:
    provider = bill["provider"]
    lines = {
        ("negotiator", "probe"): f"I'm calling because this bill is sitting at ${money['current']:.2f} a month, and I want to review what can be reduced today.",
        ("rep", "deny"): f"I've reviewed the account and the current {provider} pricing is the standard rate on file right now.",
        ("negotiator", "request_retention"): "I understand, but I'd like you to check retention options before I move this line elsewhere.",
        ("rep", "offer_discount"): f"I can apply a reduced monthly rate of ${money['offer_one']:.2f} if you'd like to keep the line active with us.",
        ("negotiator", "counter_offer"): f"That's a start, but if you can bring it to ${money['offer_two']:.2f}, I can stay and close this out right now.",
        ("rep", "retention_offer"): f"I can approve ${money['offer_two']:.2f} monthly" + (f" and a ${money['credit']:.2f} one-time credit." if money["credit"] else "."),
        ("negotiator", "push_discount"): "Those charges are exactly why I'm calling. I'd like a goodwill credit and a better monthly rate.",
        ("rep", "offer_credit"): f"I can issue a ${money['credit']:.2f} credit on the next statement as a one-time adjustment.",
        ("negotiator", "accept"): "That works for me. Please lock it in and confirm the account notes before we end the call.",
        ("rep", "close"): "It's done. You'll see the updated terms reflected on the next billing cycle.",
    }
    return lines.get((turn["role"], turn["intent"]), "Understood.")


def _phrase_turns_with_gemini(turns: list[dict[str, Any]], bill: dict[str, Any], money: dict[str, float]) -> list[str]:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError("Missing Gemini API key.")

    prompt = {
        "task": "Write short spoken telecom negotiation lines for a sandbox demo.",
        "rules": [
            "Keep each line to one or two sentences.",
            "Use only the provided facts and amounts.",
            "Do not add math or new concessions.",
            "Sound like natural phone speech.",
        ],
        "bill": {
            "provider": bill["provider"],
            "planName": bill["planName"],
            "monthlyTotal": money["current"],
            "negotiationAngles": bill.get("negotiationAngles", []),
        },
        "turns": turns,
    }

    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=json.dumps(prompt),
        config={
            "response_mime_type": "application/json",
            "response_json_schema": NEGOTIATOR_SCHEMA,
            "temperature": 0.35,
        },
    )
    payload = json.loads(response.text)
    phrased = payload.get("turns", [])
    if len(phrased) != len(turns):
        raise ValueError("Gemini returned the wrong number of phrased turns.")
    return [item["say"].strip() for item in phrased]


def build_negotiation_plan(bill: dict[str, Any]) -> dict[str, Any]:
    scenario = _determine_scenario(bill)
    blueprints, money = _plan_blueprints(bill, scenario)
    try:
        phrased = _phrase_turns_with_gemini(blueprints, bill, money)
    except Exception:
        phrased = [_fallback_line(turn, bill, money) for turn in blueprints]

    turn_plan = []
    best_offer = None
    credit = 0.0
    for blueprint, text in zip(blueprints, phrased, strict=True):
        proposed_monthly = None
        if blueprint["intent"] in {"offer_discount", "retention_offer"} and blueprint["role"] == "rep":
            proposed_monthly = money["offer_one"] if blueprint["intent"] == "offer_discount" else money["offer_two"]
            best_offer = proposed_monthly
        if blueprint["intent"] in {"offer_credit", "retention_offer"} and blueprint["role"] == "rep":
            credit = money["credit"]
        turn_plan.append(
            {
                "role": blueprint["role"],
                "intent": blueprint["intent"],
                "objective": blueprint["objective"],
                "text": text,
                "proposedMonthly": proposed_monthly,
                "credit": credit if blueprint["intent"] in {"offer_credit", "retention_offer"} and blueprint["role"] == "rep" else 0.0,
            }
        )

    current_monthly = money["current"]
    final_monthly = best_offer or current_monthly
    monthly_savings = _round_money(current_monthly - final_monthly)
    annual_savings = _round_money(monthly_savings * 12)
    result = {
        "currentMonthly": current_monthly,
        "newMonthly": final_monthly,
        "monthlySavings": monthly_savings,
        "annualSavings": annual_savings,
        "oneTimeCredit": _round_money(credit),
        "effectiveFirstYearValue": _round_money(annual_savings + credit),
        "summary": f"RateDrop reduced the bill from ${current_monthly:.2f} to ${final_monthly:.2f} per month.",
        "transcriptSummary": [
            f"Opened on {bill['provider']} billing pressure at ${current_monthly:.2f}/month.",
            f"Anchored the ask against a ${money['market_benchmark']:.2f}/month market benchmark.",
            f"Used {bill.get('negotiationAngles', ['retention leverage'])[0].lower()} as the main leverage point.",
            f"Closed at ${final_monthly:.2f}/month" + (f" with a ${credit:.2f} credit." if credit else "."),
        ],
    }
    strategy_proof = _strategy_proof(bill, scenario, money)

    return {
        "scenario": scenario,
        "money": money,
        "turnPlan": turn_plan,
        "result": result,
        "strategyProof": strategy_proof,
    }


def _strategy_proof(bill: dict[str, Any], scenario: Scenario, money: dict[str, float]) -> dict[str, Any]:
    angles = bill.get("negotiationAngles", [])
    red_flags = bill.get("redFlags", [])
    line_items = bill.get("lineItems", [])
    recurring_items = [
        item for item in line_items if item.get("recurring") and float(item.get("amount", 0)) > 0
    ]
    evidence = [
        f"Extracted {bill.get('provider', 'provider')} bill at ${money['current']:.2f}/month.",
        f"Provider benchmark profile anchors the ask near ${money['market_benchmark']:.2f}/month.",
        f"Selected {scenario.label.lower()} scenario from bill pressure signals.",
    ]
    if angles:
        evidence.append(f"Primary leverage: {angles[0]}.")
    if red_flags:
        evidence.append(f"Risk flag: {red_flags[0]}.")
    if recurring_items:
        evidence.append(f"Recurring charge pressure from {recurring_items[0].get('label', 'line item')}.")
    if money["fee_pressure"]:
        evidence.append(f"Fee or overage pressure totals ${money['fee_pressure']:.2f}.")

    return {
        "marketBenchmark": money["market_benchmark"],
        "feePressure": money["fee_pressure"],
        "targetMonthly": money["offer_two"],
        "walkAwayMonthly": money["walk_away"],
        "policySummary": (
            "Backend policy chose the scenario, target, walk-away, and concession ladder. "
            "Gemini may phrase lines, but final savings are calculated in code."
        ),
        "evidence": evidence[:6],
        "sandboxDisclosure": (
            "This demo uses a controlled carrier sandbox. It proves the bill analysis, policy engine, "
            "transcript persistence, and savings math without calling a real telecom provider."
        ),
    }


def create_negotiation_document(bill: dict[str, Any], issue_context: dict[str, Any] | None = None) -> dict[str, Any]:
    if issue_context and not is_telecom_context(issue_context):
        plan = build_support_plan(bill, issue_context)
    else:
        plan = build_negotiation_plan(bill)
    now = datetime.now(UTC)
    return {
        "billId": bill["_id"],
        "provider": issue_context.get("companyName", bill["provider"]) if issue_context else bill["provider"],
        "status": "draft",
        "scenarioId": plan["scenario"].scenario_id,
        "scenarioLabel": plan["scenario"].label,
        "currentMonthly": plan["money"]["current"],
        "targetMonthly": plan["money"]["offer_two"],
        "walkAwayMonthly": plan["money"]["walk_away"],
        "bestOfferMonthly": None,
        "oneTimeCredit": 0.0,
        "currentObjective": "Ready to place sandbox call",
        "turnPlan": plan["turnPlan"],
        "result": plan["result"],
        "strategyProof": plan["strategyProof"],
        "issueContext": issue_context,
        "call": {"status": "not-started", "mode": "simulated"},
        "createdAt": now,
        "startedAt": None,
        "endedAt": None,
    }


def build_support_plan(bill: dict[str, Any], issue_context: dict[str, Any]) -> dict[str, Any]:
    company = issue_context["companyName"]
    desired = issue_context["desiredOutcome"]
    criteria = issue_context.get("completionCriteria", [])
    primary_criterion = criteria[0] if criteria else desired
    scenario = Scenario(
        scenario_id="support_resolution",
        label="Support resolution",
        objective_labels=[
            "Opening support case",
            "Providing available context",
            "Requesting a concrete fix",
            "Confirming completion criteria",
        ],
    )
    turn_plan = [
        {
            "role": "negotiator",
            "intent": "open_support_case",
            "objective": "Opening support case",
            "text": f"Hi, I'm calling on behalf of the customer about a support issue with {company}. The problem is: {issue_context['problemSummary']}. What we need today is: {desired}.",
            "proposedMonthly": None,
            "credit": 0.0,
        },
        {
            "role": "rep",
            "intent": "ask_for_context",
            "objective": "Gathering account or case context",
            "text": f"{company} representative asks for the relevant account, booking, receipt, or case details.",
            "proposedMonthly": None,
            "credit": 0.0,
        },
        {
            "role": "negotiator",
            "intent": "provide_context",
            "objective": "Providing available context",
            "text": _support_context_line(issue_context),
            "proposedMonthly": None,
            "credit": 0.0,
        },
        {
            "role": "rep",
            "intent": "offer_resolution",
            "objective": "Offering a fix",
            "text": f"{company} representative confirms they can work toward: {primary_criterion}",
            "proposedMonthly": None,
            "credit": 0.0,
        },
        {
            "role": "negotiator",
            "intent": "confirm_completion",
            "objective": "Confirming completion criteria",
            "text": f"Before we end, please confirm this is complete: {primary_criterion}",
            "proposedMonthly": None,
            "credit": 0.0,
        },
        {
            "role": "rep",
            "intent": "close",
            "objective": "Case complete",
            "text": f"{company} representative confirms the requested support action is complete and gives the next-step timeline.",
            "proposedMonthly": None,
            "credit": 0.0,
        },
    ]
    result = {
        "currentMonthly": 0.0,
        "newMonthly": 0.0,
        "monthlySavings": 0.0,
        "annualSavings": 0.0,
        "oneTimeCredit": 0.0,
        "effectiveFirstYearValue": 0.0,
        "summary": f"RateDrop completed the {company} support request.",
        "transcriptSummary": [
            f"Opened a support case with {company}.",
            f"Stated the problem: {issue_context['problemSummary']}.",
            f"Asked for the desired outcome: {desired}.",
            f"Completion criteria: {primary_criterion}.",
        ],
    }
    return {
        "scenario": scenario,
        "money": {"current": 0.0, "offer_two": 0.0, "walk_away": 0.0},
        "turnPlan": turn_plan,
        "result": result,
        "strategyProof": _support_strategy_proof(issue_context),
    }


def _support_context_line(issue_context: dict[str, Any]) -> str:
    facts = issue_context.get("customerFacts", [])
    constraints = issue_context.get("constraints", [])
    pieces = []
    if facts:
        pieces.append("Here are the facts I have: " + "; ".join(facts[:4]) + ".")
    else:
        pieces.append("I can provide the account, booking, receipt, or identity details needed to locate the case.")
    if constraints:
        pieces.append("Constraints: " + "; ".join(constraints[:3]) + ".")
    pieces.append("Please use those details only for this support request.")
    return " ".join(pieces)


def _support_strategy_proof(issue_context: dict[str, Any]) -> dict[str, Any]:
    criteria = issue_context.get("completionCriteria", [])
    return {
        "marketBenchmark": 0.0,
        "feePressure": 0.0,
        "targetMonthly": 0.0,
        "walkAwayMonthly": 0.0,
        "policySummary": (
            "Backend policy uses the user problem, desired outcome, and completion criteria to control the call. "
            "The phone agent cannot mark the task complete until the representative confirms a matching outcome."
        ),
        "evidence": [
            f"Company: {issue_context['companyName']}.",
            f"Task type: {issue_context['taskType']}.",
            f"Problem: {issue_context['problemSummary']}.",
            f"Desired outcome: {issue_context['desiredOutcome']}.",
            *(f"Completion criterion: {criterion}." for criterion in criteria[:2]),
        ][:6],
        "sandboxDisclosure": (
            "This support-call mode is controlled by backend task policy. It can run through the live phone demo path "
            "when Twilio ConversationRelay is configured, or through local simulation for hackathon reliability."
        ),
    }


def schedule_negotiation_run(negotiation_id: str) -> bool:
    existing = active_runs.get(negotiation_id)
    if existing and not existing.done():
        return False

    task = asyncio.create_task(run_negotiation(negotiation_id))
    active_runs[negotiation_id] = task
    return True


def resume_in_progress_negotiations() -> int:
    collections = get_collections()
    resumed = 0
    for negotiation in collections["negotiations"].find({"status": "in-progress"}):
        if schedule_negotiation_run(str(negotiation["_id"])):
            resumed += 1
    return resumed


async def run_negotiation(negotiation_id: str) -> None:
    task = asyncio.current_task()
    if task is None:
        return
    active_runs[negotiation_id] = task

    try:
        collections = get_collections()
        negotiations = collections["negotiations"]
        turns_collection = collections["turns"]
        document = negotiations.find_one({"_id": object_id(negotiation_id)})
        if not document or document.get("status") == "completed":
            return

        start_index = turns_collection.count_documents({"negotiationId": document["_id"]})
        turn_plan = document.get("turnPlan", [])

        for index, planned_turn in enumerate(turn_plan[start_index:], start=start_index + 1):
            current_document = negotiations.find_one({"_id": document["_id"]})
            if not current_document or current_document.get("status") == "completed":
                return

            now = datetime.now(UTC)
            turn_doc = {
                "negotiationId": document["_id"],
                "role": planned_turn["role"],
                "intent": planned_turn["intent"],
                "objective": planned_turn["objective"],
                "text": planned_turn["text"],
                "proposedMonthly": planned_turn.get("proposedMonthly"),
                "credit": planned_turn.get("credit", 0.0),
                "createdAt": now,
            }
            turns_collection.insert_one(turn_doc)

            updates: dict[str, Any] = {
                "currentObjective": planned_turn["objective"],
            }
            if planned_turn["role"] == "rep" and planned_turn.get("proposedMonthly") is not None:
                updates["bestOfferMonthly"] = planned_turn["proposedMonthly"]
            if planned_turn["role"] == "rep" and planned_turn.get("credit"):
                updates["oneTimeCredit"] = planned_turn["credit"]

            negotiations.update_one({"_id": document["_id"]}, {"$set": updates})
            current = negotiations.find_one({"_id": document["_id"]})
            if current:
                await publish(
                    negotiation_id,
                    "turn",
                    {"turn": serialize_turn(turn_doc), "negotiation": serialize_negotiation(current).model_dump(mode="json")},
                )
            await asyncio.sleep(1.3 if index == 1 else 1.7)

        ended_at = datetime.now(UTC)
        completion_updates: dict[str, Any] = {
            "status": "completed",
            "endedAt": ended_at,
            "currentObjective": "Negotiation complete",
            "bestOfferMonthly": document["result"]["newMonthly"],
            "oneTimeCredit": document["result"]["oneTimeCredit"],
        }
        final_document = negotiations.find_one({"_id": document["_id"]})
        if final_document and final_document.get("call", {}).get("mode") == "simulated":
            completion_updates["call.status"] = "completed"

        negotiations.update_one(
            {"_id": document["_id"]},
            {"$set": completion_updates},
        )
        current = negotiations.find_one({"_id": document["_id"]})
        if current:
            await publish(negotiation_id, "status", {"negotiation": serialize_negotiation(current).model_dump(mode="json")})
    except Exception as error:
        collections = get_collections()
        current = collections["negotiations"].find_one({"_id": object_id(negotiation_id)})
        if current:
            ended_at = datetime.now(UTC)
            collections["negotiations"].update_one(
                {"_id": current["_id"]},
                {
                    "$set": {
                        "status": "failed",
                        "endedAt": ended_at,
                        "currentObjective": "Negotiation failed",
                        "call.status": "failed",
                        "call.error": f"Negotiation worker failed: {error}",
                    }
                },
            )
            refreshed = collections["negotiations"].find_one({"_id": current["_id"]})
            if refreshed:
                await publish(
                    negotiation_id,
                    "status",
                    {"negotiation": serialize_negotiation(refreshed).model_dump(mode="json")},
                )
    finally:
        active_runs.pop(negotiation_id, None)
