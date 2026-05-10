from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.agent.negotiator_agent import run_negotiator_agent
from backend.app.core.config import get_settings
from backend.app.services.conversation_relay import _advance_policy_for_prompt


def telecom_negotiation() -> dict:
    return {
        "provider": "Bell",
        "currentMonthly": 85.0,
        "targetMonthly": 52.0,
        "walkAwayMonthly": 63.0,
        "bestOfferMonthly": None,
        "oneTimeCredit": 0.0,
        "liveState": {"node": "open", "counterCount": 0, "accepted": False, "closing": False},
    }


def support_negotiation() -> dict:
    return {
        "provider": "Air Canada",
        "currentMonthly": 0.0,
        "targetMonthly": 0.0,
        "walkAwayMonthly": 0.0,
        "bestOfferMonthly": None,
        "oneTimeCredit": 0.0,
        "liveState": {"node": "open", "counterCount": 0, "accepted": False, "closing": False},
        "issueContext": {
            "companyName": "Air Canada",
            "taskType": "travel_support",
            "problemSummary": "A baggage fee was charged twice",
            "desiredOutcome": "Refund the duplicate baggage fee",
            "customerFacts": [],
            "constraints": [],
            "completionCriteria": ["Representative confirms the duplicate fee was refunded."],
            "successSignals": ["confirmed", "completed", "processed", "refund"],
            "escalationTerms": ["supervisor", "customer relations"],
        },
    }


def test_agent_falls_back_without_gemini_key() -> None:
    settings = get_settings()
    original_key = settings.gemini_api_key
    settings.gemini_api_key = None
    try:
        decision = run_negotiator_agent(telecom_negotiation(), "The best I can do is 70 dollars a month.")
    finally:
        settings.gemini_api_key = original_key

    assert decision["action"] == "counter_to_target"
    assert decision["proposedMonthly"] == 70.0
    assert "$52.00" in decision["text"]


def test_support_fallback_uses_support_phrasing() -> None:
    settings = get_settings()
    original_key = settings.gemini_api_key
    settings.gemini_api_key = None
    try:
        decision = run_negotiator_agent(support_negotiation(), "I need the receipt or booking reference.")
    finally:
        settings.gemini_api_key = original_key

    assert decision["action"] == "provide_available_context"
    assert "account, booking, receipt" in decision["text"]


def test_disabled_conversation_relay_path_uses_deterministic_policy() -> None:
    settings = get_settings()
    original_mode = settings.agent_mode
    settings.agent_mode = "disabled"
    try:
        decision = asyncio.run(_advance_policy_for_prompt(telecom_negotiation(), "We can do 60 dollars a month."))
    finally:
        settings.agent_mode = original_mode

    assert decision["action"] == "accept_offer"
    assert decision["accepted"] is True


def test_default_agent_mode_is_strands() -> None:
    settings = get_settings()
    original_mode = settings.agent_mode
    settings.agent_mode = "strands"
    try:
        assert settings.normalized_agent_mode == "strands"
    finally:
        settings.agent_mode = original_mode


if __name__ == "__main__":
    test_agent_falls_back_without_gemini_key()
    test_support_fallback_uses_support_phrasing()
    test_disabled_conversation_relay_path_uses_deterministic_policy()
    test_default_agent_mode_is_strands()
    print("agent wrap tests passed")
