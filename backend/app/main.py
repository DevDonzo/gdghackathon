from __future__ import annotations

import asyncio
import mimetypes
import json
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, File, HTTPException, Request, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import ValidationError
from pymongo import ReturnDocument

from backend.app.core.config import get_settings
from backend.app.db.mongo import database_mode, ensure_indexes, get_collections, get_database
from backend.app.models.schemas import (
    CompanyLookupRequest,
    InvalidObjectIdError,
    NegotiationCreateRequest,
    object_id,
    serialize_bill,
    serialize_negotiation,
    serialize_turn,
)
from backend.app.services.events import encode_sse, publish, subscribe, unsubscribe
from backend.app.services.conversation_relay import handle_conversation_relay
from backend.app.services.company_lookup import lookup_company_contact
from backend.app.services.extraction import DEMO_BILLS, demo_bill_fixture, extract_bill_data
from backend.app.services.issue_context import build_issue_context
from backend.app.services.negotiation import create_negotiation_document, resume_in_progress_negotiations, schedule_negotiation_run
from backend.app.services.twilio_voice import launch_sandbox_call, negotiation_twiml, twilio_readiness, update_call_status


app = FastAPI(title="RateDrop API", version="0.1.0")
settings = get_settings()
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1:3001",
        "http://localhost:3001",
        settings.frontend_base_url,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    try:
        ensure_indexes()
        resume_in_progress_negotiations()
    except Exception as error:  # pragma: no cover - allows static shell to load when Atlas is unavailable
        logger.warning("RateDrop startup dependency check failed: %s", error)


@app.exception_handler(InvalidObjectIdError)
async def invalid_object_id_handler(_: Request, exc: InvalidObjectIdError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/health")
def healthcheck() -> dict[str, str]:
    if database_mode() == "mongo":
        get_database().command("ping")
    return {"status": "ok", "database": database_mode()}


@app.get("/api/readiness")
def readiness(request: Request) -> JSONResponse:
    mongo_ready = database_mode() == "local"
    if database_mode() == "mongo":
        try:
            get_database().command("ping")
            mongo_ready = True
        except Exception:
            mongo_ready = False

    return JSONResponse(
        {
            "status": "ok" if mongo_ready else "degraded",
            "database": {"mode": database_mode(), "ready": mongo_ready},
            "gemini": {"configured": bool(settings.gemini_api_key), "model": settings.gemini_model},
            "agent": {
                "mode": settings.normalized_agent_mode,
                "provider": "google-adk" if settings.normalized_agent_mode == "adk" else settings.normalized_agent_mode,
                "modelProvider": settings.normalized_agent_model_provider,
                "modelId": settings.gemini_model,
            },
            "tavily": {"configured": bool(settings.tavily_api_key)},
            "twilio": twilio_readiness(request),
        }
    )


@app.post("/api/bills/upload")
async def upload_bill(file: UploadFile = File(...)) -> JSONResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="A bill file is required.")
    content_type = file.content_type or mimetypes.guess_type(file.filename)[0] or ""
    if not (content_type == "application/pdf" or content_type.startswith("image/")):
        raise HTTPException(status_code=400, detail="Upload a PDF or image file.")

    payload = await file.read()
    extraction = extract_bill_data(payload, file.filename, content_type or "application/octet-stream")

    collections = get_collections()
    bill_doc = {
        "filename": file.filename,
        "provider": extraction.provider,
        "currency": extraction.currency,
        "monthlyTotal": extraction.monthly_total,
        "planName": extraction.plan_name,
        "lineItems": [item.model_dump(mode="json") for item in extraction.line_items],
        "negotiationAngles": extraction.negotiation_angles,
        "redFlags": extraction.red_flags,
        "extractionConfidence": extraction.confidence,
        "contentType": content_type,
        "createdAt": datetime.now(UTC),
    }
    inserted = collections["bills"].insert_one(bill_doc)
    stored = collections["bills"].find_one({"_id": inserted.inserted_id})
    if not stored:
        raise HTTPException(status_code=500, detail="Bill extraction could not be stored.")
    return JSONResponse(serialize_bill(stored).model_dump(mode="json"))


@app.get("/api/demo-bills")
def list_demo_bills() -> JSONResponse:
    items = []
    for scenario_id, fixture in DEMO_BILLS.items():
        items.append(
            {
                "id": scenario_id,
                "label": f"{fixture['provider']} demo",
                "provider": fixture["provider"],
                "monthlyTotal": fixture["monthlyTotal"],
                "headlineAngle": fixture["negotiationAngles"][0],
            }
        )
    return JSONResponse({"items": items})


@app.post("/api/bills/demo/{scenario_id}")
def create_demo_bill(scenario_id: str) -> JSONResponse:
    try:
        filename, extraction = demo_bill_fixture(scenario_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Demo bill not found.") from error

    collections = get_collections()
    bill_doc = {
        "filename": filename,
        "preferredScenarioId": DEMO_BILLS[scenario_id].get("preferredScenarioId"),
        "provider": extraction.provider,
        "currency": extraction.currency,
        "monthlyTotal": extraction.monthly_total,
        "planName": extraction.plan_name,
        "lineItems": [item.model_dump(mode="json") for item in extraction.line_items],
        "negotiationAngles": extraction.negotiation_angles,
        "redFlags": extraction.red_flags,
        "extractionConfidence": extraction.confidence,
        "contentType": "application/pdf",
        "createdAt": datetime.now(UTC),
        "source": "demo",
    }
    inserted = collections["bills"].insert_one(bill_doc)
    stored = collections["bills"].find_one({"_id": inserted.inserted_id})
    if not stored:
        raise HTTPException(status_code=500, detail="Demo bill could not be created.")
    return JSONResponse(serialize_bill(stored).model_dump(mode="json"))


@app.get("/api/bills/{bill_id}")
def get_bill(bill_id: str) -> JSONResponse:
    bill = get_collections()["bills"].find_one({"_id": object_id(bill_id)})
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found.")
    return JSONResponse(serialize_bill(bill).model_dump(mode="json"))


@app.api_route("/api/negotiations", methods=["GET", "POST"])
async def negotiations_collection(request: Request, limit: int = 8) -> JSONResponse:
    if request.method == "GET":
        safe_limit = max(1, min(limit, 20))
        negotiations = [
            serialize_negotiation(item).model_dump(mode="json")
            for item in get_collections()["negotiations"].find().sort("createdAt", -1).limit(safe_limit)
        ]
        return JSONResponse({"items": negotiations})

    try:
        payload = await request.json()
        create_request = NegotiationCreateRequest.model_validate(payload)
    except (json.JSONDecodeError, ValidationError, ValueError) as error:
        raise HTTPException(status_code=400, detail="Invalid negotiation request payload.") from error

    collections = get_collections()
    bill = collections["bills"].find_one({"_id": object_id(create_request.billId)})
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found.")

    custom_angles = [item.strip() for item in create_request.customAngles if item.strip()][:4]
    negotiation_bill = dict(bill)
    if custom_angles:
        existing_angles = list(bill.get("negotiationAngles", []))
        negotiation_bill["negotiationAngles"] = [*existing_angles, *[angle for angle in custom_angles if angle not in existing_angles]]

    issue_context = build_issue_context(negotiation_bill, create_request)
    issue_context["contactLookup"] = lookup_company_contact(issue_context)
    document = create_negotiation_document(negotiation_bill, issue_context=issue_context)
    document["customAngles"] = custom_angles
    inserted = collections["negotiations"].insert_one(document)
    stored = collections["negotiations"].find_one({"_id": inserted.inserted_id})
    if not stored:
        raise HTTPException(status_code=500, detail="Negotiation could not be created.")
    return JSONResponse(serialize_negotiation(stored).model_dump(mode="json"))


@app.post("/api/company-lookup")
async def company_lookup(request: Request) -> JSONResponse:
    try:
        payload = await request.json()
        lookup_request = CompanyLookupRequest.model_validate(payload)
    except (json.JSONDecodeError, ValidationError, ValueError) as error:
        raise HTTPException(status_code=400, detail="Invalid company lookup payload.") from error

    bill = _bill_for_company_lookup(lookup_request)
    issue_context = build_issue_context(bill, lookup_request)
    contact_lookup = lookup_company_contact(issue_context)
    issue_context["contactLookup"] = contact_lookup
    return JSONResponse({"issueContext": issue_context, "contactLookup": contact_lookup})


def _bill_for_company_lookup(lookup_request: CompanyLookupRequest) -> dict[str, Any]:
    if lookup_request.billId:
        bill = get_collections()["bills"].find_one({"_id": object_id(lookup_request.billId)})
        if not bill:
            raise HTTPException(status_code=404, detail="Bill not found.")
        bill_copy = dict(bill)
        if lookup_request.companyName:
            bill_copy["provider"] = lookup_request.companyName
        return bill_copy

    company = lookup_request.companyName or "Unknown company"
    return {
        "provider": company,
        "currency": "CAD",
        "monthlyTotal": 0.0,
        "planName": "Support request",
        "lineItems": [],
        "negotiationAngles": [],
        "redFlags": [],
    }


@app.post("/api/negotiations/{negotiation_id}/start")
async def start_negotiation(negotiation_id: str, request: Request) -> JSONResponse:
    collections = get_collections()
    negotiation_object_id = object_id(negotiation_id)
    negotiation = collections["negotiations"].find_one({"_id": negotiation_object_id})
    if not negotiation:
        raise HTTPException(status_code=404, detail="Negotiation not found.")
    if negotiation["status"] != "draft":
        return JSONResponse(serialize_negotiation(negotiation).model_dump(mode="json"))

    now = datetime.now(UTC)
    call = launch_sandbox_call(negotiation_id, request)
    current = collections["negotiations"].find_one_and_update(
        {"_id": negotiation_object_id, "status": "draft"},
        {
            "$set": {
                "status": "in-progress",
                "startedAt": now,
                "currentObjective": _start_objective(call.get("mode")),
                "call": call,
            }
        },
        return_document=ReturnDocument.AFTER,
    )
    if not current:
        latest = collections["negotiations"].find_one({"_id": negotiation_object_id})
        if not latest:
            raise HTTPException(status_code=404, detail="Negotiation not found.")
        return JSONResponse(serialize_negotiation(latest).model_dump(mode="json"))

    if current:
        await publish(negotiation_id, "status", {"negotiation": serialize_negotiation(current).model_dump(mode="json")})
    if call.get("mode") != "conversation_relay":
        schedule_negotiation_run(negotiation_id)

    refreshed = collections["negotiations"].find_one({"_id": negotiation_object_id})
    return JSONResponse(serialize_negotiation(refreshed).model_dump(mode="json"))


def _start_objective(call_mode: str | None) -> str:
    if call_mode == "conversation_relay":
        return "Dialing live phone demo"
    if call_mode == "sandbox":
        return "Dialing sandbox carrier line"
    return "Running simulated negotiation flow"


@app.get("/api/negotiations/{negotiation_id}")
def get_negotiation(negotiation_id: str) -> JSONResponse:
    negotiation = get_collections()["negotiations"].find_one({"_id": object_id(negotiation_id)})
    if not negotiation:
        raise HTTPException(status_code=404, detail="Negotiation not found.")
    return JSONResponse(serialize_negotiation(negotiation).model_dump(mode="json"))


@app.get("/api/negotiations/{negotiation_id}/transcript")
def get_transcript(negotiation_id: str) -> JSONResponse:
    collections = get_collections()
    negotiation = collections["negotiations"].find_one({"_id": object_id(negotiation_id)})
    if not negotiation:
        raise HTTPException(status_code=404, detail="Negotiation not found.")

    turns = [
        serialize_turn(turn)
        for turn in collections["turns"].find({"negotiationId": negotiation["_id"]}).sort("createdAt", 1)
    ]
    return JSONResponse({"turns": turns})


@app.get("/api/negotiations/{negotiation_id}/events")
async def negotiation_events(negotiation_id: str) -> StreamingResponse:
    collections = get_collections()
    negotiation = collections["negotiations"].find_one({"_id": object_id(negotiation_id)})
    if not negotiation:
        raise HTTPException(status_code=404, detail="Negotiation not found.")

    async def event_stream():
        queue = subscribe(negotiation_id)
        try:
            turns = [
                serialize_turn(turn)
                for turn in collections["turns"].find({"negotiationId": negotiation["_id"]}).sort("createdAt", 1)
            ]
            current = collections["negotiations"].find_one({"_id": negotiation["_id"]})
            if current:
                yield encode_sse(
                    "snapshot",
                    {"negotiation": serialize_negotiation(current).model_dump(mode="json"), "turns": turns},
                )
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                yield message
        finally:
            unsubscribe(negotiation_id, queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/twilio/voice/negotiations/{negotiation_id}")
@app.get("/twilio/voice/negotiations/{negotiation_id}")
def twilio_voice_negotiation(negotiation_id: str, request: Request, step: int = 0, mode: str | None = None) -> Response:
    negotiation = get_collections()["negotiations"].find_one({"_id": object_id(negotiation_id)})
    if not negotiation:
        raise HTTPException(status_code=404, detail="Negotiation not found.")
    return Response(content=negotiation_twiml(negotiation, request, step, mode=mode), media_type="application/xml")


@app.websocket("/ws/conversation-relay/{negotiation_id}")
async def conversation_relay_socket(websocket: WebSocket, negotiation_id: str) -> None:
    await handle_conversation_relay(negotiation_id, websocket)


@app.post("/twilio/status/{negotiation_id}")
async def twilio_status(negotiation_id: str, request: Request) -> Response:
    form = await request.form()
    payload = {key: str(value) for key, value in form.items()}
    current = update_call_status(negotiation_id, payload)
    if current:
        await publish(negotiation_id, "status", {"negotiation": serialize_negotiation(current).model_dump(mode="json")})
    return Response(content="", media_type="text/plain")


@app.post("/twilio/conversation-relay/{negotiation_id}/complete")
async def twilio_conversation_relay_complete(negotiation_id: str, request: Request) -> Response:
    form = await request.form()
    payload = {key: str(value) for key, value in form.items()}
    current = update_call_status(negotiation_id, payload)
    if current:
        await publish(negotiation_id, "status", {"negotiation": serialize_negotiation(current).model_dump(mode="json")})
    return Response(content="", media_type="text/plain")


@app.get("/")
def api_home() -> JSONResponse:
    return JSONResponse(
        {
            "name": "RateDrop API",
            "status": "ok",
            "frontend": settings.frontend_base_url,
            "docs": "/docs",
        }
    )
