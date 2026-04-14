from __future__ import annotations

import json
import threading
from collections import defaultdict
from typing import Callable

from event_lens.schemas.events import EventEnvelope
from event_lens.schemas.messages import validate_payload
from event_lens.schemas.topics import Topic

try:
    import redis
except ImportError:  # pragma: no cover - exercised only when dependency missing
    redis = None

Handler = Callable[[EventEnvelope], None]


class RedisBus:
    """Redis pub/sub topic bus using event envelopes as JSON messages."""

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
        # Redis channel names are the same as our topic names.
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
            # Poll in short intervals so stop() can shut down promptly.
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
