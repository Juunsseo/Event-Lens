import pytest

from event_lens.schemas.messages import MessageValidationError, validate_payload
from event_lens.schemas.topics import Topic


@pytest.mark.parametrize(
    "topic,payload",
    [
        (Topic.IMAGE_SUBMITTED, {"image_id": "img-1", "image_uri": "file://img.jpg", "submitted_by": "cli"}),
        (Topic.INFERENCE_COMPLETED, {"image_id": "img-1", "model_version": "v1", "objects": []}),
        (
            Topic.ANNOTATION_STORED,
            {"image_id": "img-1", "annotation_id": "ann-1", "objects": [], "source_event_id": "evt-2"},
        ),
        (Topic.EMBEDDING_CREATED, {"image_id": "img-1", "vector_id": "vec-1", "dimensions": 8}),
        (Topic.ANNOTATION_CORRECTED, {"image_id": "img-1", "annotation_id": "ann-1", "corrections": []}),
        (Topic.QUERY_SUBMITTED, {"query_id": "q-1", "text": "cat", "top_k": 3}),
        (Topic.QUERY_COMPLETED, {"query_id": "q-1", "results": []}),
    ],
)
def test_message_contracts_valid(topic: Topic, payload: dict) -> None:
    validate_payload(topic, payload)


@pytest.mark.parametrize(
    "topic,payload",
    [
        (Topic.IMAGE_SUBMITTED, {"image_id": "img-1", "submitted_by": "cli"}),
        (Topic.INFERENCE_COMPLETED, {"image_id": "img-1", "model_version": "v1", "objects": "not-a-list"}),
        (Topic.ANNOTATION_STORED, {"image_id": "img-1", "annotation_id": "ann", "objects": []}),
        (Topic.EMBEDDING_CREATED, {"image_id": "img-1", "vector_id": "vec", "dimensions": 0}),
        (Topic.ANNOTATION_CORRECTED, {"image_id": "img-1", "annotation_id": "ann", "corrections": "bad"}),
        (Topic.QUERY_SUBMITTED, {"query_id": "q1", "text": "cat", "top_k": 0}),
        (Topic.QUERY_COMPLETED, {"query_id": "q1", "results": "bad"}),
    ],
)
def test_message_contracts_invalid(topic: Topic, payload: dict) -> None:
    with pytest.raises(MessageValidationError):
        validate_payload(topic, payload)
