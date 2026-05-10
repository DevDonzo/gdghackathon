from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.core.config import get_settings
from backend.app.services.company_lookup import (
    build_company_contact_query,
    contact_lookup_from_tavily,
    extract_phone_candidates,
    lookup_company_contact,
    normalize_phone,
)
from backend.app.services.issue_context import build_issue_context


def test_phone_normalization() -> None:
    assert normalize_phone("1-888-247-2262") == "+18882472262"
    assert normalize_phone("(416) 555-1212") == "+14165551212"
    assert normalize_phone("not a phone") is None


def test_tavily_response_parsing() -> None:
    response = {
        "answer": "Air Canada customer support can be reached at 1-888-247-2262.",
        "results": [
            {
                "title": "Contact us - Air Canada",
                "url": "https://www.aircanada.com/ca/en/aco/home/fly/customer-support/contact-us.html",
                "content": "For reservations and customer support, call 1-888-247-2262.",
            }
        ],
    }

    candidates = extract_phone_candidates(response)
    assert candidates == ["+18882472262"]

    lookup = contact_lookup_from_tavily("Air Canada", "Air Canada official customer service phone number", response)
    assert lookup["status"] == "found"
    assert lookup["phoneNumber"] == "+18882472262"
    assert lookup["sourceUrls"] == ["https://www.aircanada.com/ca/en/aco/home/fly/customer-support/contact-us.html"]
    assert lookup["confidence"] >= 0.8


def test_answer_phone_takes_priority_over_result_snippets() -> None:
    response = {
        "answer": "Air Canada's official customer service phone number is 1-888-247-2262.",
        "results": [
            {
                "title": "Airport Customer Support - Air Canada",
                "url": "https://www.aircanada.com/us/en/aco/home/fly/customer-support/airport-customer-support.html",
                "content": "Airport support can be reached at 1-800-361-5373.",
            }
        ],
    }

    assert extract_phone_candidates(response) == ["+18882472262", "+18003615373"]


def test_lookup_query_uses_issue_context() -> None:
    context = build_issue_context(
        {"provider": "Air Canada", "monthlyTotal": 0, "lineItems": [], "negotiationAngles": [], "redFlags": []},
        type(
            "Payload",
            (),
            {
                "companyName": "Air Canada",
                "issueDescription": "Baggage fee was charged twice",
                "desiredOutcome": "Refund the duplicate baggage fee",
                "customerFacts": [],
                "constraints": [],
                "completionCriteria": [],
            },
        )(),
    )

    query = build_company_contact_query(context)
    assert "Air Canada" in query
    assert "travel support" in query
    assert "Baggage fee was charged twice" in query


def test_lookup_disabled_without_key() -> None:
    settings = get_settings()
    original_key = settings.tavily_api_key
    settings.tavily_api_key = None
    try:
        result = lookup_company_contact({"companyName": "Air Canada", "taskType": "travel_support"})
    finally:
        settings.tavily_api_key = original_key

    assert result["status"] == "disabled"
    assert result["phoneNumber"] is None
    assert "TAVILY_API_KEY" in result["error"]


if __name__ == "__main__":
    test_phone_normalization()
    test_tavily_response_parsing()
    test_answer_phone_takes_priority_over_result_snippets()
    test_lookup_query_uses_issue_context()
    test_lookup_disabled_without_key()
    print("company lookup tests passed")
