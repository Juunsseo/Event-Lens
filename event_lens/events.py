from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class Topic(str, Enum):
    IMAGE_SUBMITTED = "image.submitted"
    INFERENCE_COMPLETED = "inference.completed"
    ANNOTATION_STORED = "annotation.stored"
    EMBEDDING_CREATED = "embedding.created"
    ANNOTATION_CORRECTED = "annotation.corrected"
    QUERY_SUBMITTED = "query.submitted"
    QUERY_COMPLETED = "query.completed"


class EventValidationError(ValueError):
    """Raised when an event envelope is invalid."""


class MessageValidationError(ValueError):
    """Raised when a topic payload is invalid."""


@dataclass(frozen=True)
class EventEnvelope:
    topic: Topic
    event_id: str
    timestamp: str
    payload: dict[str, Any]

    def validate(self) -> None:
        if not self.event_id:
            raise EventValidationError("event_id is required")
        if not self.timestamp:
            raise EventValidationError("timestamp is required")
        try:
            datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise EventValidationError("timestamp must be ISO-8601") from exc
        if not isinstance(self.payload, dict):
            raise EventValidationError("payload must be a dictionary")

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic.value,
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "payload": self.payload,
        }

    @classmethod
    def create(cls, topic: Topic, payload: dict[str, Any], *, event_id: str | None = None) -> "EventEnvelope":
        envelope = cls(
            topic=topic,
            event_id=event_id or str(uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            payload=payload,
        )
        envelope.validate()
        validate_payload(envelope.topic, envelope.payload)
        return envelope

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EventEnvelope":
        try:
            topic = Topic(data["topic"])
            envelope = cls(
                topic=topic,
                event_id=str(data["event_id"]),
                timestamp=str(data["timestamp"]),
                payload=data["payload"],
            )
        except KeyError as exc:
            raise EventValidationError(f"missing field: {exc.args[0]}") from exc
        except ValueError as exc:
            raise EventValidationError(f"invalid topic: {data.get('topic')}") from exc
        envelope.validate()
        return envelope


def validate_payload(topic: Topic, payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise MessageValidationError("payload must be a dictionary")

    required_by_topic: dict[Topic, dict[str, type | tuple[type, ...]]] = {
        Topic.IMAGE_SUBMITTED: {"image_id": str, "image_uri": str, "submitted_by": str},
        Topic.INFERENCE_COMPLETED: {"image_id": str, "model_version": str, "objects": list},
        Topic.ANNOTATION_STORED: {
            "image_id": str,
            "annotation_id": str,
            "objects": list,
            "source_event_id": str,
        },
        Topic.EMBEDDING_CREATED: {"image_id": str, "vector_id": str, "dimensions": int},
        Topic.ANNOTATION_CORRECTED: {"image_id": str, "annotation_id": str, "corrections": list},
        Topic.QUERY_SUBMITTED: {"query_id": str, "text": str, "top_k": int},
        Topic.QUERY_COMPLETED: {"query_id": str, "results": list},
    }

    for field, expected_type in required_by_topic[topic].items():
        value = payload.get(field)
        if expected_type is str and (not isinstance(value, str) or not value):
            raise MessageValidationError(f"'{field}' must be a non-empty string")
        if expected_type is int and not isinstance(value, int):
            raise MessageValidationError(f"'{field}' must be an integer")
        if expected_type is list and not isinstance(value, list):
            raise MessageValidationError(f"'{field}' must be a list")

    if topic == Topic.EMBEDDING_CREATED and payload["dimensions"] < 1:
        raise MessageValidationError("'dimensions' must be >= 1")
    if topic == Topic.QUERY_SUBMITTED and payload["top_k"] < 1:
        raise MessageValidationError("'top_k' must be >= 1")
