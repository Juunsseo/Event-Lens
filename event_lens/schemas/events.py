from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .topics import Topic


class EventValidationError(ValueError):
    """Raised when an event does not satisfy the contract."""


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
