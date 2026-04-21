import base64

from event_lens.messaging.bus import InMemoryBus
from event_lens.schemas.events import EventEnvelope
from event_lens.schemas.topics import Topic
from event_lens.services.pipeline import EventPipeline


def _write_test_png(tmp_path, name: str = "test.png") -> str:
    # 1x1 transparent PNG.
    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
    )
    image_path = tmp_path / name
    image_path.write_bytes(png_bytes)
    return image_path.as_uri()


def build_system() -> tuple[InMemoryBus, EventPipeline]:
    bus = InMemoryBus()
    pipeline = EventPipeline(bus)
    pipeline.register()
    return bus, pipeline


def test_end_to_end_upload_to_embedding_and_query(tmp_path) -> None:
    bus, pipeline = build_system()
    completed_queries: list[EventEnvelope] = []
    bus.subscribe(Topic.QUERY_COMPLETED, lambda e: completed_queries.append(e))

    bus.publish(
        EventEnvelope.create(
            Topic.IMAGE_SUBMITTED,
            {
                "image_id": "img-1",
                "image_uri": _write_test_png(tmp_path),
                "submitted_by": "cli",
            },
            event_id="evt-submit-1",
        )
    )

    assert "img-1" in pipeline.document_store.records
    assert "img-1" in pipeline.vector_index.vectors

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


def test_duplicate_event_id_is_idempotent(tmp_path) -> None:
    bus, pipeline = build_system()

    event = EventEnvelope.create(
        Topic.IMAGE_SUBMITTED,
        {
            "image_id": "img-dup",
            "image_uri": _write_test_png(tmp_path, "dup.png"),
            "submitted_by": "cli",
        },
        event_id="evt-dup-1",
    )

    bus.publish(event)
    bus.publish(event)

    assert "img-dup" in pipeline.document_store.records
    assert sum(1 for e in pipeline.processed_event_ids if e == "evt-dup-1") == 1


def test_malformed_event_goes_to_dead_letter() -> None:
    bus, pipeline = build_system()

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
    assert pipeline.document_store.records == {}


def test_annotation_corrected_updates_document_and_reindexes(tmp_path) -> None:
    bus, pipeline = build_system()

    bus.publish(
        EventEnvelope.create(
            Topic.IMAGE_SUBMITTED,
            {
                "image_id": "img-2",
                "image_uri": _write_test_png(tmp_path, "img2.png"),
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

    labels = [obj["label"] for obj in pipeline.document_store.records["img-2"]["objects"]]
    assert "corrected" in labels
    assert "img-2" in pipeline.vector_index.vectors
