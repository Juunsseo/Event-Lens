import os
import threading
import time

import pytest

from event_lens.bus import RedisBus
from event_lens.events import EventEnvelope, Topic


pytestmark = pytest.mark.integration


def _redis_url() -> str:
    url = os.getenv("EVENT_LENS_REDIS_URL")
    if not url:
        pytest.skip("set EVENT_LENS_REDIS_URL to run live Redis integration tests")
    if os.getenv("EVENT_LENS_RUN_INTEGRATION_TESTS") != "1":
        pytest.skip("set EVENT_LENS_RUN_INTEGRATION_TESTS=1 to run live integration tests")
    return url


def test_online_redis_pubsub_round_trip() -> None:
    bus = RedisBus(redis_url=_redis_url())
    received: list[EventEnvelope] = []
    done = threading.Event()

    def _handler(event: EventEnvelope) -> None:
        received.append(event)
        done.set()

    bus.subscribe(Topic.QUERY_COMPLETED, _handler)
    bus.start()
    time.sleep(0.2)

    try:
        event = EventEnvelope.create(
            Topic.QUERY_COMPLETED,
            {"query_id": "redis-smoke-test", "results": [{"image_id": "img-1", "score": 1.0}]},
            event_id="evt-redis-smoke-test",
        )
        bus.publish(event)

        assert done.wait(timeout=5), "Redis event was not delivered within 5 seconds"
        assert received[-1].event_id == "evt-redis-smoke-test"
        assert received[-1].topic == Topic.QUERY_COMPLETED
        assert received[-1].payload["query_id"] == "redis-smoke-test"
    finally:
        bus.stop()
