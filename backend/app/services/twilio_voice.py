from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

from fastapi import Request
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse

from backend.app.core.config import get_settings
from backend.app.db.mongo import get_collections
from backend.app.models.schemas import object_id


def resolve_public_base_url(request: Request) -> str | None:
    settings = get_settings()
    if settings.public_base_url:
        return settings.public_base_url.rstrip("/")

    host = request.headers.get("host")
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    if not host:
        return None
    if "localhost" in host or "127.0.0.1" in host:
        return None
    return f"{proto}://{host}".rstrip("/")


def launch_sandbox_call(negotiation_id: str, request: Request) -> dict[str, Any]:
    settings = get_settings()
    if not settings.twilio_enabled:
        return {"status": "simulated", "mode": "simulated", "error": "Twilio credentials are not configured."}

    public_base_url = resolve_public_base_url(request)
    if not public_base_url:
        return {
            "status": "simulated",
            "mode": "simulated",
            "error": "PUBLIC_BASE_URL is required for Twilio callbacks when running locally.",
        }

    destination = settings.twilio_sandbox_to_number or (settings.twilio_verified_numbers[0] if settings.twilio_verified_numbers else None)
    if not destination:
        return {
            "status": "simulated",
            "mode": "simulated",
            "error": "Set TWILIO_SANDBOX_TO_NUMBER or TWILIO_VERIFY_ORIG_NUMBERS to a verified sandbox destination.",
        }

    try:
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        query = urlencode({"step": 0})
        call = client.calls.create(
            to=destination,
            from_=settings.twilio_phone_number,
            url=f"{public_base_url}/twilio/voice/negotiations/{negotiation_id}?{query}",
            status_callback=f"{public_base_url}/twilio/status/{negotiation_id}",
            status_callback_event=["initiated", "ringing", "answered", "completed"],
            method="POST",
        )
        return {
            "sid": call.sid,
            "to": destination,
            "fromNumber": settings.twilio_phone_number,
            "status": call.status or "queued",
            "mode": "sandbox",
            "error": None,
        }
    except Exception as error:
        return {
            "to": destination,
            "fromNumber": settings.twilio_phone_number,
            "status": "simulated",
            "mode": "simulated",
            "error": f"Twilio launch failed, so RateDrop switched to simulated mode: {error}",
        }


def negotiation_twiml(negotiation: dict[str, Any], request: Request, step: int) -> str:
    base = resolve_public_base_url(request) or ""
    response = VoiceResponse()
    turn_plan = negotiation.get("turnPlan", [])

    if step == 0:
        response.say("Welcome to the RateDrop telecom sandbox. This call will narrate a controlled bill negotiation demo.")
        response.pause(length=1)

    if step >= len(turn_plan):
        result = negotiation.get("result", {})
        response.say(
            f"Negotiation complete. Monthly cost moved from {result.get('currentMonthly', 0):.2f} dollars to {result.get('newMonthly', 0):.2f} dollars."
        )
        credit = result.get("oneTimeCredit", 0.0)
        if credit:
            response.say(f"A one time credit of {credit:.2f} dollars was also secured.")
        response.say("Thank you for reviewing the RateDrop demo.")
        response.hangup()
        return str(response)

    turn = turn_plan[step]
    speaker = "RateDrop negotiator" if turn["role"] == "negotiator" else f"{negotiation['provider']} representative"
    response.say(f"{speaker}. {turn['text']}")
    response.pause(length=1)
    response.redirect(f"{base}/twilio/voice/negotiations/{negotiation['_id']}?step={step + 1}", method="POST")
    return str(response)


def update_call_status(negotiation_id: str, payload: dict[str, str]) -> dict[str, Any] | None:
    collections = get_collections()
    negotiations = collections["negotiations"]
    current = negotiations.find_one({"_id": object_id(negotiation_id)})
    if not current:
        return None

    update_fields: dict[str, Any] = {
        "call.status": payload.get("CallStatus", "unknown"),
        "call.sid": payload.get("CallSid"),
    }
    failure_statuses = {"failed", "busy", "no-answer", "canceled"}
    if payload.get("CallStatus") == "in-progress" and not current.get("startedAt"):
        update_fields["startedAt"] = datetime.now(UTC)
    if payload.get("CallStatus") == "completed":
        completed_at = datetime.now(UTC)
        update_fields["call.completedAt"] = completed_at
        if not current.get("endedAt"):
            update_fields["endedAt"] = completed_at
        update_fields["call.error"] = None
    elif payload.get("CallStatus") in failure_statuses:
        completed_at = datetime.now(UTC)
        update_fields["call.completedAt"] = completed_at
        if not current.get("endedAt"):
            update_fields["endedAt"] = completed_at
        update_fields["call.error"] = f"Twilio reported a {payload.get('CallStatus')} outbound sandbox call."

    negotiations.update_one({"_id": current["_id"]}, {"$set": update_fields})
    return negotiations.find_one({"_id": current["_id"]})
