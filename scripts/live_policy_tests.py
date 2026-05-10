from __future__ import annotations

import sys
from pathlib import Path

from bson import ObjectId
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.db.mongo import ensure_indexes, get_collections
from backend.app.main import app
from backend.app.core.config import get_settings
from backend.app.services.extraction import DEMO_BILLS
from backend.app.services.issue_context import build_issue_context
from backend.app.services.negotiation import create_negotiation_document
from backend.app.services.negotiation_live import (
    advance_live_policy,
    classify_rep_utterance,
    classify_support_utterance,
    opening_live_turn,
    parse_bare_money_value,
    parse_offer_values,
)
from backend.app.services.twilio_voice import conversation_relay_twiml


def assert_equal(actual, expected, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def assert_true(value, label: str) -> None:
    if not value:
        raise AssertionError(label)


def negotiation_fixture() -> dict:
    bill = dict(DEMO_BILLS["bell_promo_push"])
    bill["_id"] = ObjectId()
    return create_negotiation_document(bill)


class Payload:
    issueDescription = "Air Canada cancelled my flight and I need the refund fixed."
    desiredOutcome = "Get the refund processed or receive a confirmed rebooking."
    companyName = "Air Canada"
    customerFacts = ["Booking reference ABC123", "Flight AC101 was cancelled", "Receipt total was $420"]
    constraints = ["Do not accept a vague callback without a case number"]
    completionCriteria = ["Refund is processed or rebooking is confirmed with a reference number"]


class RogersPayload:
    issueDescription = "The monthly bill is too high and there is a disputed $35 roaming fee that should be credited."
    desiredOutcome = "Lower the monthly bill to $55 and apply a $35 credit for the disputed roaming fee."
    companyName = "Rogers"
    targetMonthly = 55
    walkAwayMonthly = 60
    customerFacts = ["Current Rogers bill is $91.50 on Infinite Essentials 75", "There is a disputed $35 roaming fee"]
    constraints = ["Do not accept only a one-time credit without monthly rate relief"]
    completionCriteria = ["Rep confirms the new monthly rate", "Rep confirms the $35 credit", "Rep confirms the effective date and account notes"]


def drain_text_or_end(websocket) -> list[dict]:
    messages = []
    while True:
        message = websocket.receive_json()
        messages.append(message)
        if message["type"] in {"text", "end"}:
            return messages


def main() -> int:
    settings = get_settings()
    original_agent_mode = settings.agent_mode
    settings.agent_mode = "disabled"

    negotiation = negotiation_fixture()

    monthly, credit = parse_offer_values("I can reduce it to 70 dollars a month.", negotiation["currentMonthly"])
    assert_equal(monthly, 70.0, "monthly offer parsing")
    assert_equal(credit, None, "monthly offer does not imply credit")

    monthly, credit = parse_offer_values("I can offer ten dollars off and a twenty-five dollar credit.", negotiation["currentMonthly"])
    assert_equal(monthly, 75.0, "discount parsing")
    assert_equal(credit, 25.0, "word-number credit parsing")
    assert_equal(parse_bare_money_value("I can do ten dollars."), 10.0, "bare money parsing")
    assert_equal(parse_bare_money_value("I can do ten dollars off."), None, "bare money ignores discounts")

    assert_equal(classify_rep_utterance("I do not see any promotions available.", negotiation), "refusal", "refusal intent")
    assert_equal(classify_rep_utterance("I can add a 25 dollar credit.", negotiation), "credit_offer", "credit intent")
    assert_equal(classify_rep_utterance("I can get approval for 52 dollars a month.", negotiation), "final_discount_offer", "final offer intent")

    first = advance_live_policy(negotiation, "I don't see any promotions on this account.")
    assert_equal(first["repIntent"], "refusal", "first policy intent")
    assert_equal(first["action"], "push_for_retention", "first policy action")
    assert_true(not first["completed"], "refusal should not complete")

    second = advance_live_policy({**negotiation, "liveState": first["nextState"]}, "I can reduce it to 70 dollars a month.")
    assert_equal(second["repIntent"], "small_discount_offer", "small offer intent")
    assert_equal(second["action"], "counter_to_target", "small offer action")
    assert_equal(second["proposedMonthly"], 70.0, "small offer monthly value")
    assert_true("$52.00" in second["text"], "first counter can state target")

    repeat = advance_live_policy({**negotiation, "liveState": second["nextState"]}, "I can reduce it to 68 dollars a month.")
    assert_equal(repeat["action"], "counter_to_target", "repeat counter action")
    assert_true("$52.00" not in repeat["text"], "repeat counter does not keep restating target")

    generous = advance_live_policy(negotiation, "I can do ten dollars.")
    assert_equal(generous["action"], "accept_offer", "very low bare offer should be accepted")
    assert_equal(generous["proposedMonthly"], 10.0, "very low bare offer value")

    final = advance_live_policy({**negotiation, "liveState": second["nextState"]}, "I can get approval for 52 dollars a month and a 25 dollar credit.")
    assert_equal(final["repIntent"], "final_discount_offer", "final intent")
    assert_equal(final["action"], "accept_offer", "final action")
    assert_true(not final["completed"], "acceptable offer requests proof before completion")
    assert_equal(final["proposedMonthly"], 52.0, "final monthly value")
    assert_equal(final["credit"], 25.0, "final credit value")
    confirmed = advance_live_policy(
        {**negotiation, "bestOfferMonthly": final["bestOfferMonthly"], "oneTimeCredit": final["bestCredit"], "liveState": final["nextState"]},
        "Confirmed, it starts next billing cycle and it is noted on the account.",
    )
    assert_equal(confirmed["action"], "confirm_accepted_offer", "confirmation action")
    assert_true(confirmed["completed"], "proof confirmation completes")

    twiml = conversation_relay_twiml(
        negotiation,
        "wss://example.com/ws/conversation-relay/abc123",
        action_url="https://example.com/twilio/conversation-relay/abc123/complete",
    )
    assert_true("<ConversationRelay" in twiml, "twiml contains ConversationRelay")
    assert_true('url="wss://example.com/ws/conversation-relay/abc123"' in twiml, "twiml contains websocket url")
    assert_true('name="negotiationId"' in twiml, "twiml includes negotiation parameter")

    ensure_indexes()
    collections = get_collections()
    live_doc = negotiation_fixture()
    live_doc["call"] = {"status": "queued", "mode": "conversation_relay"}
    inserted = collections["negotiations"].insert_one(live_doc)

    with TestClient(app) as client:
        with client.websocket_connect(f"/ws/conversation-relay/{inserted.inserted_id}") as websocket:
            opening = websocket.receive_json()
            assert_equal(opening["type"], "text", "websocket opening type")
            assert_true("monthly rate" in opening["token"].lower(), "websocket opening line")
            websocket.send_json({"type": "setup", "callSid": "CA_TEST", "sessionId": "VX_TEST"})
            websocket.send_json({"type": "prompt", "voicePrompt": "I can get approval for 52 dollars a month and a 25 dollar credit.", "last": True})
            reply = websocket.receive_json()
            assert_equal(reply["type"], "text", "websocket reply type")
            assert_true("confirm" in reply["token"].lower(), "websocket asks for confirmation proof")
            websocket.send_json({"type": "prompt", "voicePrompt": "Confirmed, it starts next billing cycle and it is noted on the account.", "last": True})
            proof_reply = websocket.receive_json()
            assert_equal(proof_reply["type"], "text", "websocket proof reply type")

    stored = collections["negotiations"].find_one({"_id": inserted.inserted_id})
    transcript_count = collections["turns"].count_documents({"negotiationId": inserted.inserted_id})
    assert_equal(stored["status"], "completed", "websocket negotiation completion")
    assert_equal(stored["bestOfferMonthly"], 52.0, "websocket best offer")
    assert_equal(stored["oneTimeCredit"], 25.0, "websocket credit")
    assert_equal(transcript_count, 5, "websocket transcript count")

    multi_doc = negotiation_fixture()
    multi_doc["call"] = {"status": "queued", "mode": "conversation_relay"}
    multi_inserted = collections["negotiations"].insert_one(multi_doc)

    with TestClient(app) as client:
        with client.websocket_connect(f"/ws/conversation-relay/{multi_inserted.inserted_id}") as websocket:
            opening = websocket.receive_json()
            assert_true("monthly rate" in opening["token"].lower(), "multi-turn opening line")
            websocket.send_json({"type": "setup", "callSid": "CA_MULTI", "sessionId": "VX_MULTI"})

            websocket.send_json({"type": "prompt", "voicePrompt": "Thanks for calling Bell, how can I help?", "last": True})
            greeting_reply = drain_text_or_end(websocket)[-1]
            assert_equal(greeting_reply["type"], "text", "greeting reply type")
            assert_true("monthly rate" in greeting_reply["token"].lower(), "greeting pushes toward bill resolution")

            websocket.send_json({"type": "prompt", "voicePrompt": "I do not see any promotions available.", "last": True})
            refusal_reply = drain_text_or_end(websocket)[-1]
            assert_true("monthly bill" in refusal_reply["token"].lower(), "refusal reply asks for bill resolution")

            websocket.send_json({"type": "prompt", "voicePrompt": "I can reduce it to 70 dollars a month.", "last": True})
            small_offer_reply = drain_text_or_end(websocket)[-1]
            assert_true("$52.00" in small_offer_reply["token"], "small offer counter uses deterministic target")

            websocket.send_json({"type": "prompt", "voicePrompt": "I can add a 25 dollar credit.", "last": True})
            credit_reply = drain_text_or_end(websocket)[-1]
            assert_true("monthly charge" in credit_reply["token"].lower(), "credit-only reply asks for recurring relief")

            websocket.send_json({"type": "prompt", "voicePrompt": "I can get approval for 52 dollars a month and a 25 dollar credit.", "last": True})
            final_reply = websocket.receive_json()
            assert_equal(final_reply["type"], "text", "multi-turn final reply type")
            assert_true("confirm" in final_reply["token"].lower(), "multi-turn final asks for proof")
            websocket.send_json({"type": "prompt", "voicePrompt": "Confirmed, it starts next billing cycle and it is noted on the account.", "last": True})
            proof_reply = websocket.receive_json()
            assert_equal(proof_reply["type"], "text", "multi-turn proof reply type")

    multi_stored = collections["negotiations"].find_one({"_id": multi_inserted.inserted_id})
    multi_transcript_count = collections["turns"].count_documents({"negotiationId": multi_inserted.inserted_id})
    assert_equal(multi_stored["status"], "completed", "multi-turn websocket completion")
    assert_equal(multi_stored["bestOfferMonthly"], 52.0, "multi-turn best offer")
    assert_equal(multi_stored["oneTimeCredit"], 25.0, "multi-turn credit")
    assert_equal(multi_transcript_count, 13, "multi-turn transcript count")

    air_bill = dict(DEMO_BILLS["bell_promo_push"])
    air_bill["_id"] = ObjectId()
    issue_context = build_issue_context(air_bill, Payload())
    assert_equal(issue_context["companyName"], "Air Canada", "support company")
    assert_equal(issue_context["taskType"], "travel_support", "support task type")
    support_doc = create_negotiation_document(air_bill, issue_context=issue_context)
    opening = opening_live_turn(support_doc)
    assert_true("Air Canada" in opening["text"], "support opening company")
    assert_true("refund" in opening["text"].lower(), "support opening desired outcome")
    assert_true("a Air Canada" not in opening["text"], "support opening grammar")
    assert_equal(
        classify_support_utterance("Okay, I can refund you.", support_doc),
        "pending_review",
        "support promise needs concrete confirmation",
    )
    assert_equal(
        classify_support_utterance("I processed the refund and your case number is AC123.", support_doc),
        "resolved_confirmation",
        "support resolved classification",
    )

    support_doc["call"] = {"status": "queued", "mode": "conversation_relay"}
    support_inserted = collections["negotiations"].insert_one(support_doc)

    with TestClient(app) as client:
        with client.websocket_connect(f"/ws/conversation-relay/{support_inserted.inserted_id}") as websocket:
            support_opening = websocket.receive_json()
            assert_true("Air Canada" in support_opening["token"], "support websocket opening")
            websocket.send_json({"type": "setup", "callSid": "CA_SUPPORT", "sessionId": "VX_SUPPORT"})

            websocket.send_json({"type": "prompt", "voicePrompt": "Thanks for calling Air Canada, how can I help?", "last": True})
            support_goal = drain_text_or_end(websocket)[-1]
            assert_true("refund" in support_goal["token"].lower(), "support explains issue")

            websocket.send_json({"type": "prompt", "voicePrompt": "I need the booking reference and receipt number.", "last": True})
            support_context = drain_text_or_end(websocket)[-1]
            assert_true("ABC123" in support_context["token"], "support provides known facts")

            websocket.send_json({"type": "prompt", "voicePrompt": "I processed the refund and your case number is AC123.", "last": True})
            support_done = websocket.receive_json()
            assert_equal(support_done["type"], "text", "support final reply type")
            assert_true("Perfect" in support_done["token"], "support final reply is conversational")

    support_stored = collections["negotiations"].find_one({"_id": support_inserted.inserted_id})
    support_transcript_count = collections["turns"].count_documents({"negotiationId": support_inserted.inserted_id})
    assert_equal(support_stored["status"], "completed", "support websocket completion")
    assert_true("completed the Air Canada support request" in support_stored["result"]["summary"], "support result summary")
    assert_equal(support_transcript_count, 7, "support transcript count")

    rogers_bill = dict(DEMO_BILLS["rogers_loyalty_review"])
    rogers_bill["_id"] = ObjectId()
    rogers_context = build_issue_context(rogers_bill, RogersPayload())
    assert_equal(rogers_context["taskType"], "telecom_negotiation", "rogers mixed refund/rate task stays telecom")
    rogers_doc = create_negotiation_document(
        rogers_bill,
        issue_context=rogers_context,
        target_monthly=RogersPayload.targetMonthly,
        walk_away_monthly=RogersPayload.walkAwayMonthly,
    )
    rogers_opening = opening_live_turn(rogers_doc)
    assert_true("$55.00" in rogers_opening["text"], "rogers opening states target")
    assert_true("35 disputed charge credited" in rogers_opening["text"].lower(), "rogers opening asks for fee credit")

    credit_only = advance_live_policy(
        rogers_doc,
        "I can apply a 35 dollar credit for the roaming fee, but the monthly plan would stay the same.",
    )
    assert_equal(credit_only["action"], "ask_for_credit_plus_rate_relief", "rogers credit-only offer is not enough")
    assert_equal(credit_only["bestCredit"], 35.0, "rogers credit tracked")

    weak_rate = advance_live_policy(
        {**rogers_doc, "oneTimeCredit": credit_only["bestCredit"], "liveState": credit_only["nextState"]},
        "I can reduce it to 70 dollars a month and keep the 35 dollar credit.",
    )
    assert_equal(weak_rate["action"], "counter_to_target", "rogers weak monthly offer gets countered")

    winning_rate = advance_live_policy(
        {**rogers_doc, "oneTimeCredit": weak_rate["bestCredit"], "liveState": weak_rate["nextState"]},
        "I can get approval for 55 dollars a month and a 35 dollar credit.",
    )
    assert_equal(winning_rate["action"], "accept_offer", "rogers target monthly and credit is accepted")
    assert_equal(winning_rate["bestOfferMonthly"], 55.0, "rogers final monthly")
    assert_equal(winning_rate["bestCredit"], 35.0, "rogers final credit")

    confirmed_rate = advance_live_policy(
        {
            **rogers_doc,
            "bestOfferMonthly": winning_rate["bestOfferMonthly"],
            "oneTimeCredit": winning_rate["bestCredit"],
            "liveState": winning_rate["nextState"],
        },
        "Confirmed, the new monthly rate is 55 dollars, the 35 dollar credit is applied, it starts next billing cycle, and it is noted on the account.",
    )
    assert_equal(confirmed_rate["action"], "confirm_accepted_offer", "rogers proof confirmation action")
    assert_true(confirmed_rate["completed"], "rogers proof confirmation completes")

    print("live policy tests passed")
    settings.agent_mode = original_agent_mode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
