from __future__ import annotations

import json
import threading
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Callable

from event_lens.events import EventEnvelope, EventValidationError, Topic, validate_payload

try:
    import redis
except ImportError:  # pragma: no cover - exercised only when dependency missing
    redis = None

Handler = Callable[[EventEnvelope], None]


class MessageBus(ABC):
    @abstractmethod
    def publish(self, event: EventEnvelope) -> None:
        raise NotImplementedError

    @abstractmethod
    def subscribe(self, topic: Topic, handler: Handler) -> None:
        raise NotImplementedError


class InMemoryBus(MessageBus):
    """Deterministic pub/sub bus for tests and local demos."""

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
                self.dead_letters.append({"event": event.to_dict(), "error": str(exc)})

    def subscribe(self, topic: Topic, handler: Handler) -> None:
        self._subscribers[topic].append(handler)

    def publish_raw(self, raw: dict) -> None:
        """Simulate malformed external input in tests."""
        try:
            event = EventEnvelope.from_dict(raw)
            self.publish(event)
        except (EventValidationError, ValueError) as exc:
            self.dead_letters.append({"event": raw, "error": str(exc)})


class RedisBus(MessageBus):
    """Redis pub/sub bus using topic names as channels."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0") -> None:
        if redis is None:
            raise RuntimeError("redis package is required for RedisBus")
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)
        self._pubsub = self._client.pubsub(ignore_subscribe_messages=True)
        self._subscribers: dict[Topic, list[Handler]] = defaultdict(list)
        self._listener: threading.Thread | None = None
        self._running = False

    def publish(self, event: EventEnvelope) -> None:
        event.validate()
        validate_payload(event.topic, event.payload)
        self._client.publish(event.topic.value, json.dumps(event.to_dict()))

    def subscribe(self, topic: Topic, handler: Handler) -> None:
        self._subscribers[topic].append(handler)
        self._pubsub.subscribe(topic.value)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._listener = threading.Thread(target=self._run_listener, daemon=True)
        self._listener.start()

    def stop(self) -> None:
        self._running = False
        self._pubsub.close()
        if self._listener and self._listener.is_alive():
            self._listener.join(timeout=1)

    def _run_listener(self) -> None:
        while self._running:
            message = self._pubsub.get_message(timeout=0.5)
            if not message:
                continue
            channel = message.get("channel")
            data = message.get("data")
            if not channel or not data:
                continue
            topic = Topic(channel)
            envelope = EventEnvelope.from_dict(json.loads(data))
            validate_payload(envelope.topic, envelope.payload)
            for handler in self._subscribers[topic]:
                handler(envelope)
