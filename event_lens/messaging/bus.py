from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Callable

from event_lens.schemas.events import EventEnvelope
from event_lens.schemas.messages import validate_payload
from event_lens.schemas.topics import Topic

Handler = Callable[[EventEnvelope], None]


class MessageBus(ABC):
    @abstractmethod
    def publish(self, event: EventEnvelope) -> None:
        raise NotImplementedError

    @abstractmethod
    def subscribe(self, topic: Topic, handler: Handler) -> None:
        raise NotImplementedError


class InMemoryBus(MessageBus):
    """Deterministic in-memory pub/sub bus for unit testing."""

    def __init__(self) -> None:
        self._subscribers: dict[Topic, list[Handler]] = defaultdict(list)
        self.dead_letters: list[dict] = []

    def publish(self, event: EventEnvelope) -> None:
        event.validate()
        validate_payload(event.topic, event.payload)
        for handler in self._subscribers[event.topic]:
            try:
                handler(event)
            except Exception as exc:  # pragma: no cover - defensive fallback
                # Preserve failed deliveries for debugging instead of crashing tests.
                self.dead_letters.append({"event": event.to_dict(), "error": str(exc)})

    def subscribe(self, topic: Topic, handler: Handler) -> None:
        self._subscribers[topic].append(handler)

    def publish_raw(self, raw: dict) -> None:
        """Used by tests to simulate malformed external input."""
        from event_lens.schemas.events import EventEnvelope, EventValidationError

        try:
            event = EventEnvelope.from_dict(raw)
            self.publish(event)
        except Exception as exc:
            if isinstance(exc, EventValidationError | ValueError):
                # Malformed external events are captured as dead letters.
                self.dead_letters.append({"event": raw, "error": str(exc)})
            else:
                raise
