from event_lens.messaging.bus import InMemoryBus
from event_lens.schemas.events import EventEnvelope
from event_lens.schemas.topics import Topic
from event_lens.services.pipeline import DocumentStore, EventPipeline, VectorIndex


def build_system() -> tuple[InMemoryBus, EventPipeline, DocumentStore, VectorIndex]:
    bus = InMemoryBus()
    doc_store = DocumentStore()
    vector_index = VectorIndex()
    pipeline = EventPipeline(bus, doc_store, vector_index)
    pipeline.register()
    return bus, pipeline, doc_store, vector_index


def test_end_to_end_upload_to_embedding_and_query() -> None:
    bus, _pipeline, doc_store, vector_index = build_system()
    completed_queries: list[EventEnvelope] = []
    bus.subscribe(Topic.QUERY_COMPLETED, lambda e: completed_queries.append(e))

    bus.publish(
        EventEnvelope.create(
            Topic.IMAGE_SUBMITTED,
            {
                "image_id": "img-1",
                "image_uri": "s3://bucket/img-1.jpg",
                "submitted_by": "cli",
            },
            event_id="evt-submit-1",
        )
    )

    assert "img-1" in doc_store.records
    assert "img-1" in vector_index.vectors

    bus.publish(
        EventEnvelope.create(
            Topic.QUERY_SUBMITTED,
            {"query_id": "q-1", "text": "find object", "top_k": 1},
            event_id="evt-query-1",
        )
    )

    assert len(completed_queries) == 1
    assert completed_queries[0].payload["query_id"] == "q-1"
    assert completed_queries[0].payload["results"][0]["image_id"] == "img-1"


def test_duplicate_event_id_is_idempotent() -> None:
    bus, pipeline, doc_store, _vector_index = build_system()

    event = EventEnvelope.create(
        Topic.IMAGE_SUBMITTED,
        {
            "image_id": "img-dup",
            "image_uri": "s3://bucket/img-dup.jpg",
            "submitted_by": "cli",
        },
        event_id="evt-dup-1",
    )

    bus.publish(event)
    bus.publish(event)

    assert "img-dup" in doc_store.records
    assert sum(1 for e in pipeline.processed_event_ids if e == "evt-dup-1") == 1


def test_malformed_event_goes_to_dead_letter() -> None:
    bus, _pipeline, doc_store, _vector_index = build_system()

    bus.publish_raw(
        {
            "topic": "image.submitted",
            "event_id": "evt-bad",
            "timestamp": "2026-04-14T12:00:00Z",
            # missing required payload fields
            "payload": {"image_id": "img-missing"},
        }
    )

    assert len(bus.dead_letters) == 1
    assert doc_store.records == {}

def test_annotation_corrected_updates_document_and_reindexes() -> None:
    bus, _pipeline, doc_store, vector_index = build_system()

    bus.publish(
        EventEnvelope.create(
            Topic.IMAGE_SUBMITTED,
            {
                "image_id": "img-2",
                "image_uri": "s3://bucket/img-2.jpg",
                "submitted_by": "cli",
            },
            event_id="evt-submit-2",
        )
    )

    bus.publish(
        EventEnvelope.create(
            Topic.ANNOTATION_CORRECTED,
            {
                "image_id": "img-2",
                "annotation_id": "ann-img-2",
                "corrections": [{"label": "corrected", "confidence": 1.0, "bbox": [1, 1, 2, 2]}],
            },
            event_id="evt-corrected-2",
        )
    )

    labels = [obj["label"] for obj in doc_store.records["img-2"]["objects"]]
    assert "corrected" in labels
    assert "img-2" in vector_index.vectors
