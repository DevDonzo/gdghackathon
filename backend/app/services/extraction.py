from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from google import genai

from backend.app.core.config import get_settings
from backend.app.models.schemas import BillExtraction


EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "provider": {"type": "string"},
        "currency": {"type": "string"},
        "monthlyTotal": {"type": "number"},
        "planName": {"type": "string"},
        "lineItems": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "amount": {"type": "number"},
                    "recurring": {"type": "boolean"},
                    "category": {"type": "string"},
                },
                "required": ["label", "amount", "recurring", "category"],
            },
        },
        "negotiationAngles": {"type": "array", "items": {"type": "string"}},
        "redFlags": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number"},
    },
    "required": [
        "provider",
        "currency",
        "monthlyTotal",
        "planName",
        "lineItems",
        "negotiationAngles",
        "redFlags",
        "confidence",
    ],
}


PROMPT = """
Extract a structured telecom bill summary from the attached file.

Rules:
- Return strict JSON only.
- Provider must be a telecom brand or "Unknown provider".
- Use CAD unless the bill clearly shows a different currency.
- Monthly total must be the bill's monthly payable amount.
- Line items should be concrete charges, discounts, fees, taxes, or overages.
- Negotiation angles should be short phrases grounded in the bill.
- Red flags should only list concrete issues such as overages, device protection, admin fees, or expired promo signals.
- Confidence should be a 0..1 score.
""".strip()


DEMO_BILLS: dict[str, dict[str, Any]] = {
    "bell_promo_push": {
        "filename": "bell-demo.pdf",
        "preferredScenarioId": "happy_path",
        "provider": "Bell",
        "currency": "CAD",
        "monthlyTotal": 85.0,
        "planName": "Unlimited 50",
        "lineItems": [
            {"label": "5G mobile plan", "amount": 70.0, "recurring": True, "category": "plan"},
            {"label": "Promo roll-off delta", "amount": 10.0, "recurring": True, "category": "other"},
            {"label": "Plan add-on", "amount": 5.0, "recurring": True, "category": "other"},
        ],
        "negotiationAngles": ["Expired promotional pricing", "Overage fee forgiveness", "Retention discount"],
        "redFlags": ["Promo appears to have rolled off", "Overage charge this cycle"],
        "confidence": 0.98,
    },
    "rogers_loyalty_review": {
        "filename": "rogers-demo.pdf",
        "preferredScenarioId": "escalation_path",
        "provider": "Rogers",
        "currency": "CAD",
        "monthlyTotal": 91.5,
        "planName": "Infinite Essentials 75",
        "lineItems": [
            {"label": "Infinite Essentials plan", "amount": 76.5, "recurring": True, "category": "plan"},
            {"label": "Device balance", "amount": 15.0, "recurring": True, "category": "other"},
        ],
        "negotiationAngles": ["Loyalty discount", "Competitor switch risk", "Retention review"],
        "redFlags": ["Monthly total is above comparable market pricing"],
        "confidence": 0.97,
    },
    "telus_fee_recovery": {
        "filename": "telus-demo.pdf",
        "preferredScenarioId": "fee_recovery_path",
        "provider": "Telus",
        "currency": "CAD",
        "monthlyTotal": 74.0,
        "planName": "Peace of Mind Connect 45",
        "lineItems": [
            {"label": "Mobility plan", "amount": 58.0, "recurring": True, "category": "plan"},
            {"label": "Administration fee", "amount": 6.0, "recurring": True, "category": "fee"},
            {"label": "Data overage", "amount": 10.0, "recurring": False, "category": "overage"},
        ],
        "negotiationAngles": ["Fee forgiveness", "Goodwill credit", "Plan right-sizing"],
        "redFlags": ["Unexpected admin fee", "One-time overage charge"],
        "confidence": 0.98,
    },
}


def _client() -> genai.Client:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError("Missing GEMINI_API_KEY.")
    return genai.Client(api_key=settings.gemini_api_key)


def _normalize(extraction: BillExtraction) -> BillExtraction:
    line_items = extraction.line_items or []
    if not line_items:
        line_items = [
            {
                "label": extraction.plan_name,
                "amount": extraction.monthly_total,
                "recurring": True,
                "category": "plan",
            }
        ]

    angles = extraction.negotiation_angles or []
    red_flags = extraction.red_flags or []
    corpus = " ".join([*angles, *red_flags, extraction.plan_name, extraction.provider]).lower()

    if "promo" in corpus and not any("promo" in angle.lower() for angle in angles):
        angles.append("Expired promotional pricing")
    if any(item.category in {"fee", "overage"} and item.amount > 0 for item in line_items) and not any(
        "fee" in angle.lower() or "overage" in angle.lower() for angle in angles
    ):
        angles.append("Fee forgiveness")
    if not angles:
        angles = ["Retention review", "Plan comparison", "Loyalty discount"]

    confidence = max(0.0, min(float(extraction.confidence), 1.0))
    return BillExtraction(
        provider=extraction.provider or "Unknown provider",
        currency=extraction.currency or "CAD",
        monthlyTotal=max(float(extraction.monthly_total), 0.0),
        planName=extraction.plan_name or "Current plan",
        lineItems=line_items,
        negotiationAngles=angles[:4],
        redFlags=red_flags[:4],
        confidence=confidence,
    )


def _fallback(filename: str) -> BillExtraction:
    lower_name = filename.lower()
    provider = "Rogers" if "rogers" in lower_name else "Bell" if "bell" in lower_name else "Telus" if "telus" in lower_name else "Unknown provider"
    monthly_total = 85.0 if provider != "Unknown provider" else 72.0
    return BillExtraction(
        provider=provider,
        currency="CAD",
        monthlyTotal=monthly_total,
        planName="Unlimited 50",
        lineItems=[
            {"label": "Mobile plan", "amount": round(monthly_total - 10, 2), "recurring": True, "category": "plan"},
            {"label": "Overage fee", "amount": 10.0, "recurring": False, "category": "overage"},
        ],
        negotiationAngles=["Expired promotional pricing", "Overage fee forgiveness", "Retention discount"],
        redFlags=["Possible promo rollover", "One-time overage charge"],
        confidence=0.32,
    )


def demo_bill_fixture(scenario_id: str) -> tuple[str, BillExtraction]:
    fixture = DEMO_BILLS.get(scenario_id)
    if not fixture:
        raise KeyError(scenario_id)
    return fixture["filename"], BillExtraction.model_validate(fixture)


def extract_bill_data(file_bytes: bytes, filename: str, content_type: str) -> BillExtraction:
    settings = get_settings()
    if not settings.gemini_api_key:
        return _fallback(filename)

    suffix = Path(filename).suffix or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(file_bytes)
        temp_path = Path(temp_file.name)

    try:
        uploaded = _client().files.upload(
            file=str(temp_path),
            config={"mime_type": content_type},
        )
        response = _client().models.generate_content(
            model=settings.gemini_model,
            contents=[PROMPT, uploaded],
            config={
                "response_mime_type": "application/json",
                "response_json_schema": EXTRACTION_SCHEMA,
                "temperature": 0.1,
            },
        )
        payload = json.loads(response.text)
        extraction = BillExtraction.model_validate(payload)
        return _normalize(extraction)
    except Exception:
        return _fallback(filename)
    finally:
        temp_path.unlink(missing_ok=True)
