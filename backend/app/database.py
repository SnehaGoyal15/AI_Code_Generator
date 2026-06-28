"""MongoDB configuration and storage helpers for CodeMentor AI."""

from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import uuid4
import os

from .config import get_settings

try:  # pragma: no cover - optional runtime dependency
    from bson import ObjectId  # type: ignore
    from pymongo import MongoClient as PyMongoClient  # type: ignore
    from pymongo.collection import Collection  # type: ignore
    from pymongo.database import Database  # type: ignore
    REAL_MONGO_AVAILABLE = True
except Exception:  # pragma: no cover - fallback for local/test environments
    ObjectId = None  # type: ignore[assignment]
    PyMongoClient = None  # type: ignore[assignment]
    Collection = Any  # type: ignore[assignment]
    Database = Any  # type: ignore[assignment]
    REAL_MONGO_AVAILABLE = False


settings = get_settings()


def _generate_id() -> Any:
    """Generate a Mongo-like identifier."""
    if REAL_MONGO_AVAILABLE and ObjectId is not None:
        return ObjectId()
    return uuid4().hex[:24]


def to_storage_id(value: Any) -> Any:
    """Convert a public id string into the backing storage identifier."""
    if value is None:
        return None
    value_str = str(value)
    if REAL_MONGO_AVAILABLE and ObjectId is not None:
        try:
            return ObjectId(value_str)
        except Exception:
            return value_str
    return value_str


def to_public_id(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


class _MemoryCursor:
    def __init__(self, docs: list[dict[str, Any]]):
        self._docs = docs

    def sort(self, key: str, direction: int):
        reverse = direction < 0
        self._docs.sort(key=lambda item: item.get(key), reverse=reverse)
        return self

    def limit(self, count: int):
        self._docs = self._docs[:count]
        return self

    def first(self):
        return deepcopy(self._docs[0]) if self._docs else None

    def __iter__(self):
        return iter(deepcopy(self._docs))


class _MemoryInsertResult:
    def __init__(self, inserted_id: Any):
        self.inserted_id = inserted_id


class _MemoryDeleteResult:
    def __init__(self, deleted_count: int):
        self.deleted_count = deleted_count


class _MemoryUpdateResult:
    def __init__(self, matched_count: int, modified_count: int):
        self.matched_count = matched_count
        self.modified_count = modified_count


def _matches(document: dict[str, Any], query: dict[str, Any] | None) -> bool:
    if not query:
        return True

    for key, expected in query.items():
        actual = document.get(key)
        if isinstance(expected, dict):
            for operator, value in expected.items():
                if operator == "$lt" and not (actual is not None and actual < value):
                    return False
                elif operator == "$lte" and not (actual is not None and actual <= value):
                    return False
                elif operator == "$gt" and not (actual is not None and actual > value):
                    return False
                elif operator == "$gte" and not (actual is not None and actual >= value):
                    return False
                elif operator == "$in" and actual not in value:
                    return False
                elif operator not in {"$lt", "$lte", "$gt", "$gte", "$in"}:
                    return False
        elif str(actual) != str(expected):
            return False
    return True


class _MemoryCollection:
    def __init__(self, name: str):
        self.name = name
        self._docs: list[dict[str, Any]] = []
        self._unique_fields: set[str] = set()

    def create_index(self, keys, unique: bool = False, **_kwargs):
        if unique:
            if isinstance(keys, str):
                self._unique_fields.add(keys)
            elif isinstance(keys, Iterable):
                for item in keys:
                    if isinstance(item, tuple) and item:
                        self._unique_fields.add(item[0])
                    else:
                        self._unique_fields.add(str(item))
        return f"{self.name}_{len(self._unique_fields)}"

    def _enforce_unique(self, candidate: dict[str, Any], ignore_id: Any = None) -> None:
        for field in self._unique_fields:
            candidate_value = candidate.get(field)
            if candidate_value is None:
                continue
            for existing in self._docs:
                if ignore_id is not None and str(existing.get("_id")) == str(ignore_id):
                    continue
                if str(existing.get(field)) == str(candidate_value):
                    raise ValueError(f"Duplicate value for unique field '{field}'.")

    def insert_one(self, document: dict[str, Any]):
        new_document = deepcopy(document)
        new_document.setdefault("_id", _generate_id())
        self._enforce_unique(new_document)
        self._docs.append(new_document)
        return _MemoryInsertResult(new_document["_id"])

    def find_one(self, query: dict[str, Any] | None = None, sort: list[tuple[str, int]] | None = None):
        docs = [doc for doc in self._docs if _matches(doc, query)]
        if sort:
            for key, direction in reversed(sort):
                docs.sort(key=lambda item: item.get(key), reverse=direction < 0)
        return deepcopy(docs[0]) if docs else None

    def find(self, query: dict[str, Any] | None = None):
        docs = [doc for doc in self._docs if _matches(doc, query)]
        return _MemoryCursor(docs)

    def delete_one(self, query: dict[str, Any]):
        for index, doc in enumerate(self._docs):
            if _matches(doc, query):
                del self._docs[index]
                return _MemoryDeleteResult(1)
        return _MemoryDeleteResult(0)

    def update_one(self, query: dict[str, Any], update: dict[str, Any]):
        for index, doc in enumerate(self._docs):
            if _matches(doc, query):
                updated = deepcopy(doc)
                if "$set" in update:
                    updated.update(deepcopy(update["$set"]))
                self._enforce_unique(updated, ignore_id=updated.get("_id"))
                self._docs[index] = updated
                return _MemoryUpdateResult(1, 1)
        return _MemoryUpdateResult(0, 0)

    def replace_one(self, query: dict[str, Any], replacement: dict[str, Any]):
        for index, doc in enumerate(self._docs):
            if _matches(doc, query):
                new_document = deepcopy(replacement)
                new_document.setdefault("_id", doc.get("_id"))
                self._enforce_unique(new_document, ignore_id=new_document.get("_id"))
                self._docs[index] = new_document
                return _MemoryUpdateResult(1, 1)
        return _MemoryUpdateResult(0, 0)

    def drop(self):
        self._docs.clear()


class _MemoryAdmin:
    def command(self, name: str):
        if name != "ping":
            raise ValueError("Unsupported admin command.")
        return {"ok": 1}


class _MemoryMongoDatabase:
    def __init__(self, name: str):
        self.name = name
        self._collections: dict[str, _MemoryCollection] = {}

    def __getitem__(self, name: str) -> _MemoryCollection:
        return self.get_collection(name)

    def get_collection(self, name: str) -> _MemoryCollection:
        if name not in self._collections:
            self._collections[name] = _MemoryCollection(name)
        return self._collections[name]

    def list_collection_names(self):
        return list(self._collections.keys())

    def drop_collection(self, name: str):
        self._collections.pop(name, None)


class _MemoryMongoClient:
    def __init__(self):
        self._databases: dict[str, _MemoryMongoDatabase] = {}
        self.admin = _MemoryAdmin()

    def __getitem__(self, name: str) -> _MemoryMongoDatabase:
        return self.get_database(name)

    def get_database(self, name: str) -> _MemoryMongoDatabase:
        if name not in self._databases:
            self._databases[name] = _MemoryMongoDatabase(name)
        return self._databases[name]

    def drop_database(self, name: str):
        self._databases.pop(name, None)

    def close(self):
        return None


@dataclass(frozen=True)
class MongoRuntime:
    client: Any
    db: Any
    is_memory: bool


@lru_cache(maxsize=1)
def get_mongo_runtime() -> MongoRuntime:
    mongo_uri = (settings.mongo_uri or "").strip()
    mongo_db_name = (settings.mongo_db_name or "codementor_ai").strip() or "codementor_ai"
    use_memory = mongo_uri.startswith("memory://") or not REAL_MONGO_AVAILABLE

    if use_memory:
        client: Any = _MemoryMongoClient()
        db = client.get_database(mongo_db_name)
        return MongoRuntime(client=client, db=db, is_memory=True)

    client = PyMongoClient(mongo_uri, serverSelectionTimeoutMS=5000)  # type: ignore[call-arg]
    db = client[mongo_db_name]
    return MongoRuntime(client=client, db=db, is_memory=False)


def get_mongo_db() -> Database:
    """Return the configured MongoDB database object."""
    return get_mongo_runtime().db


def get_db():
    """Yield the database object for FastAPI dependency injection."""
    yield get_mongo_db()


def initialize_storage() -> None:
    """Create indexes and verify connectivity during application startup."""
    runtime = get_mongo_runtime()
    db = runtime.db

    if runtime.is_memory:
        db.get_collection("users").create_index("email", unique=True)
        db.get_collection("code_history").create_index("user_id")
        db.get_collection("feedback").create_index("history_id")
        return

    runtime.client.admin.command("ping")
    db.users.create_index("email", unique=True)
    db.code_history.create_index("user_id")
    db.feedback.create_index("history_id")


def reset_storage() -> None:
    """Clear all application collections, used by deterministic tests."""
    runtime = get_mongo_runtime()
    db = runtime.db
    for collection_name in ("users", "code_history", "feedback"):
        try:
            db.drop_collection(collection_name)
        except Exception:
            collection = db[collection_name]
            if hasattr(collection, "drop"):
                collection.drop()
    initialize_storage()

