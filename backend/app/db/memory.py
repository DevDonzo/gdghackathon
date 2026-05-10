from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any, Iterable

from bson import ObjectId
from bson import json_util


@dataclass(slots=True)
class MemoryInsertOneResult:
    inserted_id: ObjectId


class MemoryCursor:
    def __init__(self, documents: Iterable[dict[str, Any]]):
        self._documents = [deepcopy(document) for document in documents]

    def sort(self, key_or_list: str | list[tuple[str, int]], direction: int | None = None) -> "MemoryCursor":
        if isinstance(key_or_list, list):
            sort_keys = key_or_list
        else:
            sort_keys = [(key_or_list, direction or 1)]

        for key, sort_direction in reversed(sort_keys):
            self._documents.sort(key=lambda item: _field_value(item, key), reverse=sort_direction < 0)
        return self

    def limit(self, count: int) -> "MemoryCursor":
        self._documents = self._documents[:count]
        return self

    def __iter__(self):
        return iter(self._documents)


class MemoryCollection:
    def __init__(self, storage_path: Path | None = None) -> None:
        self._storage_path = storage_path
        self._documents: list[dict[str, Any]] = []
        self._lock = RLock()
        self._load()

    def create_index(self, *_args: Any, **_kwargs: Any) -> str:
        return "memory_index"

    def insert_one(self, document: dict[str, Any]) -> MemoryInsertOneResult:
        with self._lock:
            stored = deepcopy(document)
            stored.setdefault("_id", ObjectId())
            document.setdefault("_id", stored["_id"])
            self._documents.append(stored)
            self._persist()
            return MemoryInsertOneResult(inserted_id=stored["_id"])

    def find_one(self, filter_query: dict[str, Any]) -> dict[str, Any] | None:
        with self._lock:
            for document in self._documents:
                if _matches(document, filter_query):
                    return deepcopy(document)
        return None

    def find(self, filter_query: dict[str, Any] | None = None) -> MemoryCursor:
        with self._lock:
            documents = [document for document in self._documents if _matches(document, filter_query or {})]
        return MemoryCursor(documents)

    def find_one_and_update(
        self,
        filter_query: dict[str, Any],
        update: dict[str, Any],
        return_document: Any = None,
    ) -> dict[str, Any] | None:
        with self._lock:
            for index, document in enumerate(self._documents):
                if _matches(document, filter_query):
                    updated = deepcopy(document)
                    _apply_update(updated, update)
                    self._documents[index] = updated
                    self._persist()
                    return deepcopy(updated if _return_after(return_document) else document)
        return None

    def update_one(self, filter_query: dict[str, Any], update: dict[str, Any]) -> None:
        with self._lock:
            for index, document in enumerate(self._documents):
                if _matches(document, filter_query):
                    updated = deepcopy(document)
                    _apply_update(updated, update)
                    self._documents[index] = updated
                    self._persist()
                    return

    def count_documents(self, filter_query: dict[str, Any]) -> int:
        with self._lock:
            return sum(1 for document in self._documents if _matches(document, filter_query))

    def _load(self) -> None:
        if not self._storage_path or not self._storage_path.exists():
            return
        raw = self._storage_path.read_text(encoding="utf-8")
        if raw.strip():
            self._documents = json_util.loads(raw)

    def _persist(self) -> None:
        if not self._storage_path:
            return
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._storage_path.write_text(json_util.dumps(self._documents), encoding="utf-8")


def create_memory_collections(storage_dir: Path | None = None) -> dict[str, MemoryCollection]:
    return {
        "bills": MemoryCollection(_storage_path(storage_dir, "bill_documents")),
        "negotiations": MemoryCollection(_storage_path(storage_dir, "negotiations")),
        "turns": MemoryCollection(_storage_path(storage_dir, "transcript_turns")),
    }


def _storage_path(storage_dir: Path | None, collection: str) -> Path | None:
    if storage_dir is None:
        return None
    return storage_dir / f"{collection}.json"


def _matches(document: dict[str, Any], filter_query: dict[str, Any]) -> bool:
    for key, expected in filter_query.items():
        if _field_value(document, key) != expected:
            return False
    return True


def _field_value(document: dict[str, Any], key: str) -> Any:
    value: Any = document
    for part in key.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _apply_update(document: dict[str, Any], update: dict[str, Any]) -> None:
    for key, value in update.get("$set", {}).items():
        _set_field_value(document, key, value)


def _set_field_value(document: dict[str, Any], key: str, value: Any) -> None:
    parts = key.split(".")
    target = document
    for part in parts[:-1]:
        nested = target.get(part)
        if not isinstance(nested, dict):
            nested = {}
            target[part] = nested
        target = nested
    target[parts[-1]] = value


def _return_after(return_document: Any) -> bool:
    return getattr(return_document, "name", None) == "AFTER" or return_document is True
