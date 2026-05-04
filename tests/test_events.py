import pytest

from event_lens.events import EventEnvelope, EventValidationError
from event_lens.events import Topic


def test_event_create_round_trip() -> None:
    event = EventEnvelope.create(
        Topic.IMAGE_SUBMITTED,
        {"image_id": "img-1", "image_uri": "s3://bucket/img-1.jpg", "submitted_by": "cli"},
        event_id="evt-1",
    )

    parsed = EventEnvelope.from_dict(event.to_dict())
    assert parsed == event


@pytest.mark.parametrize(
    "raw",
    [
        {"topic": "image.submitted", "timestamp": "2026-04-14T00:00:00Z", "payload": {}},
        {"topic": "image.submitted", "event_id": "evt", "payload": {}},
        {"topic": "image.submitted", "event_id": "evt", "timestamp": "not-a-date", "payload": {}},
        {"topic": "bad.topic", "event_id": "evt", "timestamp": "2026-04-14T00:00:00Z", "payload": {}},
    ],
)
def test_event_validation_errors(raw: dict) -> None:
    with pytest.raises(EventValidationError):
        EventEnvelope.from_dict(raw)
