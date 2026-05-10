from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.agent.negotiator_agent import (
    _clean_agent_result_text,
    _make_model,
    _unauthorized_money_values,
    run_negotiator_agent,
)
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


def test_agent_falls_back_when_configured_model_is_unavailable() -> None:
    settings = get_settings()
    original_key = settings.gemini_api_key
    original_provider = settings.agent_model_provider
    settings.agent_model_provider = "gemini"
    settings.gemini_api_key = None
    try:
        decision = run_negotiator_agent(telecom_negotiation(), "The best I can do is 70 dollars a month.")
    finally:
        settings.gemini_api_key = original_key
        settings.agent_model_provider = original_provider

    assert decision["action"] == "counter_to_target"
    assert decision["proposedMonthly"] == 70.0
    assert "$52.00" in decision["text"]


def test_support_fallback_uses_support_phrasing() -> None:
    settings = get_settings()
    original_key = settings.gemini_api_key
    original_provider = settings.agent_model_provider
    settings.agent_model_provider = "gemini"
    settings.gemini_api_key = None
    try:
        decision = run_negotiator_agent(support_negotiation(), "I need the receipt or booking reference.")
    finally:
        settings.gemini_api_key = original_key
        settings.agent_model_provider = original_provider

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


def test_default_agent_model_is_bedrock_nova_micro() -> None:
    settings = get_settings()
    assert settings.normalized_agent_model_provider == "bedrock"
    assert settings.agent_model_id == "amazon.nova-micro-v1:0"
    assert settings.agent_fallback_model_id == "amazon.nova-lite-v1:0"
    assert settings.agent_aws_region == "us-east-1"


def test_make_model_can_build_bedrock_model() -> None:
    settings = get_settings()
    original_provider = settings.agent_model_provider
    settings.agent_model_provider = "bedrock"
    try:
        model = _make_model()
    finally:
        settings.agent_model_provider = original_provider

    assert model.config["model_id"] == "amazon.nova-micro-v1:0"


def test_make_model_can_build_bedrock_fallback_model() -> None:
    model = _make_model(bedrock_model_id="amazon.nova-lite-v1:0")
    assert model.config["model_id"] == "amazon.nova-lite-v1:0"


def test_telecom_agent_text_rejects_unauthorized_money() -> None:
    decision = {
        "proposedMonthly": 70.0,
        "bestOfferMonthly": 70.0,
        "bestCredit": 0.0,
        "credit": None,
        "finalMonthly": 85.0,
    }
    unauthorized = _unauthorized_money_values(
        "I can counter at $60 per month, but want $52 per month.",
        decision,
        telecom_negotiation(),
    )
    assert unauthorized == ["60"]


def test_agent_result_text_cleanup_removes_thinking() -> None:
    cleaned = _clean_agent_result_text(
        "<thinking>I need a tool.</thinking>\n\n"
        "Could you please check retention options and see if there is a better loyalty rate?"
    )
    assert cleaned == "Could you please check retention options and see if there is a better loyalty rate?"


if __name__ == "__main__":
    test_agent_falls_back_when_configured_model_is_unavailable()
    test_support_fallback_uses_support_phrasing()
    test_disabled_conversation_relay_path_uses_deterministic_policy()
    test_default_agent_mode_is_strands()
    test_default_agent_model_is_bedrock_nova_micro()
    test_make_model_can_build_bedrock_model()
    test_make_model_can_build_bedrock_fallback_model()
    test_telecom_agent_text_rejects_unauthorized_money()
    test_agent_result_text_cleanup_removes_thinking()
    print("agent wrap tests passed")
