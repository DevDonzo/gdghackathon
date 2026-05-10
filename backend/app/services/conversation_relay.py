from __future__ import annotations

import json
import asyncio
from datetime import UTC, datetime
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from backend.app.core.config import get_settings
from backend.app.db.mongo import get_collections
from backend.app.models.schemas import object_id, serialize_negotiation, serialize_turn
from backend.app.services.events import publish
from backend.app.services.negotiation_live import (
    advance_live_policy,
    initial_live_state,
    live_result_summary,
    opening_live_turn,
)


async def handle_conversation_relay(negotiation_id: str, websocket: WebSocket) -> None:
    await websocket.accept()
    collections = get_collections()
    negotiations = collections["negotiations"]
    turns = collections["turns"]
    negotiation = negotiations.find_one({"_id": object_id(negotiation_id)})
    if not negotiation:
        await websocket.close(code=1008)
        return

    await _update_status(negotiation_id, {"call.status": "relay-connected", "liveState": initial_live_state()})
    current = negotiations.find_one({"_id": negotiation["_id"]}) or negotiation

    if turns.count_documents({"negotiationId": negotiation["_id"]}) == 0:
        opening = opening_live_turn(current)
        await _persist_turn_and_publish(negotiation_id, opening)
        await _send_text(websocket, opening["text"])

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue

            event_type = event.get("type")
            if event_type == "setup":
                await _update_status(
                    negotiation_id,
                    {
                        "call.status": "relay-active",
                        "call.sid": event.get("callSid"),
                        "call.sessionId": event.get("sessionId"),
                        "currentObjective": "Listening to live carrier rep",
                    },
                )
                continue

            if event_type == "prompt" and event.get("last", True):
                prompt = str(event.get("voicePrompt", "")).strip()
                if prompt:
                    await _handle_rep_prompt(negotiation_id, websocket, prompt)
                continue

            if event_type == "interrupt":
                await _update_status(negotiation_id, {"currentObjective": "Rep interrupted AI response"})
                continue

            if event_type == "error":
                await _fail_session(negotiation_id, f"ConversationRelay error: {event.get('description', 'unknown error')}")
                continue
    except WebSocketDisconnect:
        refreshed = negotiations.find_one({"_id": negotiation["_id"]})
        if refreshed and refreshed.get("status") != "completed":
            await _update_status(
                negotiation_id,
                {
                    "call.status": "relay-disconnected",
                    "call.error": "ConversationRelay WebSocket disconnected before completion.",
                    "currentObjective": "Live phone session disconnected",
                },
            )


async def _handle_rep_prompt(negotiation_id: str, websocket: WebSocket, prompt: str) -> None:
    collections = get_collections()
    negotiations = collections["negotiations"]
    negotiation = negotiations.find_one({"_id": object_id(negotiation_id)})
    if not negotiation:
        return

    decision = await _advance_policy_for_prompt(negotiation, prompt)
    rep_turn = {
        "role": "rep",
        "intent": decision["repIntent"],
        "objective": "Live carrier rep response",
        "text": prompt,
        "proposedMonthly": decision["proposedMonthly"],
        "credit": decision["credit"] or 0.0,
    }
    await _persist_turn_and_publish(negotiation_id, rep_turn)

    updates: dict[str, Any] = {
        "liveState": decision["nextState"],
        "currentObjective": decision["objective"],
        "bestOfferMonthly": decision["bestOfferMonthly"],
        "oneTimeCredit": decision["bestCredit"],
    }

    if decision["completed"]:
        ended_at = datetime.now(UTC)
        updates.update(
            {
                "status": "completed",
                "endedAt": ended_at,
                "call.status": "completed",
                "call.completedAt": ended_at,
                "result": live_result_summary(
                    {**negotiation, "liveState": decision["nextState"]},
                    decision["finalMonthly"],
                    decision["bestCredit"],
                ),
            }
        )

    await _update_status(negotiation_id, updates)

    ai_turn = {
        "role": "negotiator",
        "intent": decision["action"],
        "objective": decision["objective"],
        "text": decision["text"],
        "proposedMonthly": decision["finalMonthly"] if decision["accepted"] else None,
        "credit": decision["bestCredit"] if decision["accepted"] else 0.0,
    }
    await _persist_turn_and_publish(negotiation_id, ai_turn)
    await _send_text(websocket, decision["text"])

    if decision["completed"]:
        await websocket.send_text(json.dumps({"type": "end", "handoffData": json.dumps({"reason": decision["action"]})}))


async def _persist_turn_and_publish(negotiation_id: str, turn: dict[str, Any]) -> None:
    collections = get_collections()
    negotiations = collections["negotiations"]
    turns = collections["turns"]
    negotiation = negotiations.find_one({"_id": object_id(negotiation_id)})
    if not negotiation:
        return

    document = {
        "negotiationId": negotiation["_id"],
        "role": turn["role"],
        "intent": turn["intent"],
        "objective": turn["objective"],
        "text": turn["text"],
        "proposedMonthly": turn.get("proposedMonthly"),
        "credit": turn.get("credit", 0.0),
        "createdAt": datetime.now(UTC),
    }
    turns.insert_one(document)
    current = negotiations.find_one({"_id": negotiation["_id"]})
    if current:
        await publish(
            negotiation_id,
            "turn",
            {"turn": serialize_turn(document), "negotiation": serialize_negotiation(current).model_dump(mode="json")},
        )


async def _update_status(negotiation_id: str, updates: dict[str, Any]) -> None:
    collections = get_collections()
    negotiations = collections["negotiations"]
    negotiation = negotiations.find_one({"_id": object_id(negotiation_id)})
    if not negotiation:
        return
    negotiations.update_one({"_id": negotiation["_id"]}, {"$set": updates})
    current = negotiations.find_one({"_id": negotiation["_id"]})
    if current:
        await publish(negotiation_id, "status", {"negotiation": serialize_negotiation(current).model_dump(mode="json")})


async def _fail_session(negotiation_id: str, error: str) -> None:
    await _update_status(
        negotiation_id,
        {
            "status": "failed",
            "endedAt": datetime.now(UTC),
            "call.status": "failed",
            "call.error": error,
            "currentObjective": "ConversationRelay session failed",
        },
    )


async def _send_text(websocket: WebSocket, text: str) -> None:
    await websocket.send_text(json.dumps({"type": "text", "token": text, "last": True, "interruptible": True}))


async def _advance_policy_for_prompt(negotiation: dict[str, Any], prompt: str) -> dict[str, Any]:
    if get_settings().normalized_agent_mode == "strands":
        from backend.app.agent.negotiator_agent import run_negotiator_agent

        return await asyncio.to_thread(run_negotiator_agent, negotiation, prompt)
    return advance_live_policy(negotiation, prompt)
