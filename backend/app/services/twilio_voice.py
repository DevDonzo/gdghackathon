from __future__ import annotations

from datetime import UTC, datetime
from html import escape
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
    header_mode = request.headers.get("x-ratedrop-call-mode", "").strip().lower()
    requested_mode = header_mode if header_mode in {"simulated", "sandbox_tts", "conversation_relay"} else settings.normalized_twilio_mode
    if (
        settings.force_simulated_calls
        or requested_mode == "simulated"
        or request.headers.get("x-ratedrop-simulated-call") == "1"
    ):
        return {"status": "simulated", "mode": "simulated", "error": "Twilio launch skipped by simulated-call guard."}

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

    if requested_mode == "conversation_relay" and not conversation_relay_ws_url(negotiation_id, request):
        return {
            "status": "simulated",
            "mode": "simulated",
            "error": "ConversationRelay requires RATEDROP_CONVERSATION_RELAY_WS_BASE or a public HTTPS PUBLIC_BASE_URL.",
        }

    try:
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        voice_mode = "conversation_relay" if requested_mode == "conversation_relay" else "sandbox"
        call_kwargs: dict[str, Any] = {
            "to": destination,
            "from_": settings.twilio_phone_number,
            "status_callback": f"{public_base_url}/twilio/status/{negotiation_id}",
            "status_callback_event": ["initiated", "ringing", "answered", "completed"],
            "method": "POST",
        }
        if voice_mode == "conversation_relay":
            websocket_url = conversation_relay_ws_url(negotiation_id, request)
            if not websocket_url:
                return {
                    "status": "simulated",
                    "mode": "simulated",
                    "error": "ConversationRelay requires a public WebSocket URL.",
                }
            call_kwargs["twiml"] = conversation_relay_twiml(
                {"_id": negotiation_id, "provider": "RateDrop", "scenarioLabel": "Live support call", "currentObjective": "Live phone demo"},
                websocket_url,
                action_url=f"{public_base_url}/twilio/conversation-relay/{negotiation_id}/complete",
            )
        else:
            query = urlencode({"step": 0, "mode": voice_mode})
            call_kwargs["url"] = f"{public_base_url}/twilio/voice/negotiations/{negotiation_id}?{query}"

        call = client.calls.create(**call_kwargs)
        return {
            "sid": call.sid,
            "to": destination,
            "fromNumber": settings.twilio_phone_number,
            "status": call.status or "queued",
            "mode": voice_mode,
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


def twilio_readiness(request: Request | None = None) -> dict[str, Any]:
    settings = get_settings()
    public_base_url = resolve_public_base_url(request) if request else settings.public_base_url
    configured_mode = settings.normalized_twilio_mode
    relay_ws_base = settings.conversation_relay_ws_base or _ws_base_from_public_url(public_base_url)
    verified_numbers = settings.twilio_verified_numbers
    destination = settings.twilio_sandbox_to_number or (verified_numbers[0] if verified_numbers else None)
    missing = []

    if not settings.twilio_account_sid:
        missing.append("TWILIO_ACCOUNT_SID")
    if not settings.twilio_auth_token:
        missing.append("TWILIO_AUTH_TOKEN")
    if not settings.twilio_phone_number:
        missing.append("TWILIO_PHONE_NUMBER")
    if not destination:
        missing.append("TWILIO_SANDBOX_TO_NUMBER or TWILIO_VERIFY_ORIG_NUMBERS")
    if not public_base_url:
        missing.append("PUBLIC_BASE_URL")
    if configured_mode == "conversation_relay" and not relay_ws_base:
        missing.append("RATEDROP_CONVERSATION_RELAY_WS_BASE")

    return {
        "enabled": settings.twilio_enabled,
        "configuredMode": configured_mode,
        "mode": "simulated" if settings.force_simulated_calls else configured_mode if not missing else "simulated",
        "trialCompatible": bool(settings.twilio_enabled and destination),
        "forceSimulatedCalls": settings.force_simulated_calls,
        "destination": destination,
        "publicBaseUrl": public_base_url,
        "conversationRelayWsBase": relay_ws_base,
        "missing": missing,
        "note": "A free Twilio trial can place sandbox calls only to verified destination numbers.",
    }


def conversation_relay_ws_url(negotiation_id: str, request: Request | None = None) -> str | None:
    settings = get_settings()
    base = settings.conversation_relay_ws_base
    if not base:
        public_base_url = resolve_public_base_url(request) if request else settings.public_base_url
        base = _ws_base_from_public_url(public_base_url)
    if not base:
        return None
    return f"{base.rstrip('/')}/{negotiation_id}"


def conversation_relay_twiml(negotiation: dict[str, Any], websocket_url: str, action_url: str | None = None) -> str:
    provider = escape(str(negotiation.get("provider", "carrier")), quote=True)
    negotiation_id = escape(str(negotiation.get("_id", "")), quote=True)
    scenario = escape(str(negotiation.get("scenarioLabel", "Negotiation")), quote=True)
    objective = escape(str(negotiation.get("currentObjective", "Live phone call")), quote=True)
    action_attr = f' action="{escape(action_url, quote=True)}"' if action_url else ""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"<Connect{action_attr}>"
        f'<ConversationRelay url="{escape(websocket_url, quote=True)}" '
        'language="en-US" interruptible="true">'
        f'<Parameter name="negotiationId" value="{negotiation_id}"/>'
        f'<Parameter name="provider" value="{provider}"/>'
        f'<Parameter name="scenario" value="{scenario}"/>'
        f'<Parameter name="objective" value="{objective}"/>'
        "</ConversationRelay>"
        "</Connect>"
        "</Response>"
    )


def negotiation_twiml(negotiation: dict[str, Any], request: Request, step: int, mode: str | None = None) -> str:
    requested_mode = mode or negotiation.get("call", {}).get("mode")
    if requested_mode == "conversation_relay":
        websocket_url = conversation_relay_ws_url(str(negotiation["_id"]), request)
        if websocket_url:
            base = resolve_public_base_url(request) or ""
            action_url = f"{base}/twilio/conversation-relay/{negotiation['_id']}/complete" if base else None
            return conversation_relay_twiml(negotiation, websocket_url, action_url=action_url)

    base = resolve_public_base_url(request) or ""
    response = VoiceResponse()
    turn_plan = negotiation.get("turnPlan", [])

    if step == 0:
        response.say(
            "Connected. Please speak as the company support representative. "
            "The customer representative will start, then pause for your answer."
        )
        response.pause(length=1)

    if step >= len(turn_plan):
        result = negotiation.get("result", {})
        response.say(
            f"Negotiation complete. Monthly cost moved from {result.get('currentMonthly', 0):.2f} dollars to {result.get('newMonthly', 0):.2f} dollars."
        )
        credit = result.get("oneTimeCredit", 0.0)
        if credit:
            response.say(f"A one time credit of {credit:.2f} dollars was also secured.")
        response.say("Thanks, that resolves what I called about.")
        response.pause(length=120)
        response.redirect(f"{base}/twilio/voice/negotiations/{negotiation['_id']}?step={step}", method="POST")
        return str(response)

    turn = turn_plan[step]
    next_url = f"{base}/twilio/voice/negotiations/{negotiation['_id']}?step={step + 1}"
    if turn["role"] == "rep":
        response.say(f"Your turn as the {negotiation['provider']} representative. Please answer after this prompt.")
        gather = response.gather(input="speech", timeout=8, speech_timeout="auto", action=next_url, method="POST")
        gather.pause(length=7)
        response.redirect(next_url, method="POST")
        return str(response)

    response.say(f"RateDrop agent. {turn['text']}")
    response.pause(length=1)
    response.redirect(next_url, method="POST")
    return str(response)


def _ws_base_from_public_url(public_base_url: str | None) -> str | None:
    if not public_base_url:
        return None
    base = public_base_url.rstrip("/")
    if base.startswith("https://"):
        return "wss://" + base.removeprefix("https://") + "/ws/conversation-relay"
    return None


def update_call_status(negotiation_id: str, payload: dict[str, str]) -> dict[str, Any] | None:
    collections = get_collections()
    negotiations = collections["negotiations"]
    current = negotiations.find_one({"_id": object_id(negotiation_id)})
    if not current:
        return None

    call_status = payload.get("CallStatus")
    update_fields: dict[str, Any] = {}
    if call_status:
        update_fields["call.status"] = call_status
    if payload.get("CallSid"):
        update_fields["call.sid"] = payload.get("CallSid")
    failure_statuses = {"failed", "busy", "no-answer", "canceled"}
    if call_status == "in-progress" and not current.get("startedAt"):
        update_fields["startedAt"] = datetime.now(UTC)
    if call_status == "completed":
        completed_at = datetime.now(UTC)
        update_fields["call.completedAt"] = completed_at
        if not current.get("endedAt"):
            update_fields["endedAt"] = completed_at
        update_fields["call.error"] = None
    elif call_status in failure_statuses:
        completed_at = datetime.now(UTC)
        update_fields["call.completedAt"] = completed_at
        if not current.get("endedAt"):
            update_fields["endedAt"] = completed_at
        update_fields["call.error"] = f"Twilio reported a {call_status} outbound sandbox call."

    if update_fields:
        negotiations.update_one({"_id": current["_id"]}, {"$set": update_fields})
    return negotiations.find_one({"_id": current["_id"]})
