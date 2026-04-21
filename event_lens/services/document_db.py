from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol


class DocumentDatabase(Protocol):
    def upsert_annotation(self, image_id: str, annotation_id: str, objects: list[dict[str, Any]]) -> None:
        raise NotImplementedError

    def get_annotation(self, image_id: str) -> dict[str, Any] | None:
        raise NotImplementedError


@dataclass
class InMemoryDocumentStore(DocumentDatabase):
    """Deterministic document store used in local tests."""

    records: dict[str, dict[str, Any]] = field(default_factory=dict)

    def upsert_annotation(self, image_id: str, annotation_id: str, objects: list[dict[str, Any]]) -> None:
        self.records[image_id] = {
            "image_id": image_id,
            "annotation_id": annotation_id,
            "objects": objects,
            "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }

    def get_annotation(self, image_id: str) -> dict[str, Any] | None:
        return self.records.get(image_id)


class MongoDocumentStore(DocumentDatabase):
    """MongoDB-backed document store for week-2 integration."""

    def __init__(self, mongo_uri: str, *, database: str = "event_lens", collection: str = "annotations") -> None:
        try:
            from pymongo import MongoClient
        except ImportError as exc:  # pragma: no cover - optional runtime dependency
            raise RuntimeError("pymongo is required for MongoDocumentStore") from exc

        self._client = MongoClient(mongo_uri)
        self._collection = self._client[database][collection]

    def upsert_annotation(self, image_id: str, annotation_id: str, objects: list[dict[str, Any]]) -> None:
        document = {
            "image_id": image_id,
            "annotation_id": annotation_id,
            "objects": objects,
            "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        self._collection.update_one({"image_id": image_id}, {"$set": document}, upsert=True)

    def get_annotation(self, image_id: str) -> dict[str, Any] | None:
        document = self._collection.find_one({"image_id": image_id}, {"_id": 0})
        return dict(document) if document else None
