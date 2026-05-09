from __future__ import annotations

from functools import lru_cache
import logging

from pymongo import ASCENDING, DESCENDING
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from pymongo.database import Database

from backend.app.core.config import get_settings
from backend.app.db.memory import MemoryCollection, create_memory_collections


logger = logging.getLogger(__name__)
_memory_collections: dict[str, MemoryCollection] | None = None
_using_memory_db = False


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
    if _using_memory_db:
        return get_memory_collections()

    db = get_database()
    return {
        "bills": db["bill_documents"],
        "negotiations": db["negotiations"],
        "turns": db["transcript_turns"],
    }


def get_memory_collections() -> dict[str, MemoryCollection]:
    global _memory_collections
    if _memory_collections is None:
        _memory_collections = create_memory_collections()
    return _memory_collections


def database_mode() -> str:
    return "memory" if _using_memory_db else "mongo"


def _switch_to_memory_db(error: Exception) -> None:
    global _using_memory_db
    settings = get_settings()
    if not settings.memory_db_allowed:
        raise error
    _using_memory_db = True
    logger.warning("MongoDB is unavailable; using development in-memory storage. Error: %s", error)


def ensure_indexes() -> None:
    global _using_memory_db
    if not _using_memory_db:
        try:
            get_database().command("ping")
        except PyMongoError as error:
            _switch_to_memory_db(error)

    collections = get_collections()
    collections["bills"].create_index([("createdAt", DESCENDING)])
    collections["negotiations"].create_index([("createdAt", DESCENDING)])
    collections["negotiations"].create_index([("status", ASCENDING), ("createdAt", DESCENDING)])
    collections["turns"].create_index([("negotiationId", ASCENDING), ("createdAt", ASCENDING)])
