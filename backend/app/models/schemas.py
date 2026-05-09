from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field


class InvalidObjectIdError(ValueError):
    pass


class LineItem(BaseModel):
    label: str
    amount: float
    recurring: bool = True
    category: Literal["plan", "tax", "fee", "overage", "discount", "other"] = "other"


class BillExtraction(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    provider: str
    currency: str = "CAD"
    monthly_total: float = Field(alias="monthlyTotal")
    plan_name: str = Field(default="Current plan", alias="planName")
    line_items: list[LineItem] = Field(default_factory=list, alias="lineItems")
    negotiation_angles: list[str] = Field(default_factory=list, alias="negotiationAngles")
    red_flags: list[str] = Field(default_factory=list, alias="redFlags")
    confidence: float = 0.0


class BillUploadResponse(BaseModel):
    id: str
    filename: str
    provider: str
    currency: str
    monthlyTotal: float
    planName: str
    lineItems: list[LineItem]
    negotiationAngles: list[str]
    redFlags: list[str]
    extractionConfidence: float
    createdAt: datetime


class NegotiationCreateRequest(BaseModel):
    billId: str
    customAngles: list[str] = Field(default_factory=list)


class CallMetadata(BaseModel):
    sid: str | None = None
    to: str | None = None
    fromNumber: str | None = None
    status: str = "not-started"
    mode: Literal["sandbox", "simulated"] = "simulated"
    error: str | None = None


class NegotiationTurn(BaseModel):
    role: Literal["negotiator", "rep", "system"]
    intent: str
    objective: str
    text: str
    proposedMonthly: float | None = None
    credit: float = 0.0
    createdAt: datetime


class NegotiationResult(BaseModel):
    currentMonthly: float
    newMonthly: float
    monthlySavings: float
    annualSavings: float
    oneTimeCredit: float
    effectiveFirstYearValue: float
    summary: str
    transcriptSummary: list[str]


class NegotiationResponse(BaseModel):
    id: str
    billId: str
    status: str
    scenarioId: str
    scenarioLabel: str
    provider: str
    currentMonthly: float
    targetMonthly: float
    walkAwayMonthly: float
    bestOfferMonthly: float | None = None
    oneTimeCredit: float = 0.0
    currentObjective: str
    call: CallMetadata
    result: NegotiationResult | None = None
    createdAt: datetime
    startedAt: datetime | None = None
    endedAt: datetime | None = None


def object_id(value: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise InvalidObjectIdError("Invalid id.")
    return ObjectId(value)


def serialize_bill(document: dict[str, Any]) -> BillUploadResponse:
    return BillUploadResponse(
        id=str(document["_id"]),
        filename=document["filename"],
        provider=document["provider"],
        currency=document["currency"],
        monthlyTotal=document["monthlyTotal"],
        planName=document["planName"],
        lineItems=[LineItem.model_validate(item) for item in document.get("lineItems", [])],
        negotiationAngles=document.get("negotiationAngles", []),
        redFlags=document.get("redFlags", []),
        extractionConfidence=document.get("extractionConfidence", 0.0),
        createdAt=document["createdAt"],
    )


def serialize_turn(document: dict[str, Any]) -> dict[str, Any]:
    payload = NegotiationTurn(
        role=document["role"],
        intent=document["intent"],
        objective=document["objective"],
        text=document["text"],
        proposedMonthly=document.get("proposedMonthly"),
        credit=document.get("credit", 0.0),
        createdAt=document["createdAt"],
    )
    return payload.model_dump(mode="json")


def serialize_negotiation(document: dict[str, Any]) -> NegotiationResponse:
    call = CallMetadata.model_validate(document.get("call", {}))
    result = document.get("result")
    return NegotiationResponse(
        id=str(document["_id"]),
        billId=str(document["billId"]),
        status=document["status"],
        scenarioId=document["scenarioId"],
        scenarioLabel=document["scenarioLabel"],
        provider=document["provider"],
        currentMonthly=document["currentMonthly"],
        targetMonthly=document["targetMonthly"],
        walkAwayMonthly=document["walkAwayMonthly"],
        bestOfferMonthly=document.get("bestOfferMonthly"),
        oneTimeCredit=document.get("oneTimeCredit", 0.0),
        currentObjective=document.get("currentObjective", "Preparing call"),
        call=call,
        result=NegotiationResult.model_validate(result) if result else None,
        createdAt=document["createdAt"],
        startedAt=document.get("startedAt"),
        endedAt=document.get("endedAt"),
    )
