from __future__ import annotations

from functools import lru_cache

from pymongo import ASCENDING, DESCENDING
from pymongo import MongoClient
from pymongo.database import Database

from backend.app.core.config import get_settings


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    settings = get_settings()
    return MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)


def get_database() -> Database:
    client = get_client()
    database = client.get_default_database()
    if database is None:
        raise RuntimeError("MongoDB URI must include a default database name.")
    return database


def get_collections() -> dict[str, object]:
    db = get_database()
    return {
        "bills": db["bill_documents"],
        "negotiations": db["negotiations"],
        "turns": db["transcript_turns"],
    }


def ensure_indexes() -> None:
    collections = get_collections()
    collections["bills"].create_index([("createdAt", DESCENDING)])
    collections["negotiations"].create_index([("createdAt", DESCENDING)])
    collections["negotiations"].create_index([("status", ASCENDING), ("createdAt", DESCENDING)])
    collections["turns"].create_index([("negotiationId", ASCENDING), ("createdAt", ASCENDING)])
