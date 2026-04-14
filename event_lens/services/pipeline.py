from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from event_lens.messaging.bus import MessageBus
from event_lens.schemas.events import EventEnvelope
from event_lens.schemas.topics import Topic


@dataclass
class DocumentStore:
    records: dict[str, dict[str, Any]] = field(default_factory=dict)

    def upsert_annotation(self, image_id: str, annotation_id: str, objects: list[dict[str, Any]]) -> None:
        self.records[image_id] = {
            "annotation_id": annotation_id,
            "objects": objects,
        }


@dataclass
class VectorIndex:
    vectors: dict[str, list[float]] = field(default_factory=dict)

    def add(self, image_id: str, vector: list[float]) -> None:
        self.vectors[image_id] = vector

    def search(self, query_text: str, top_k: int) -> list[dict[str, Any]]:
        # Keep this deterministic for tests; replace with FAISS later.
        ordered = sorted(self.vectors.items(), key=lambda kv: kv[0])
        return [
            {"image_id": image_id, "score": float(len(query_text)) / (len(vector) or 1)}
            for image_id, vector in ordered[:top_k]
        ]


class EventPipeline:
    def __init__(self, bus: MessageBus, document_store: DocumentStore, vector_index: VectorIndex) -> None:
        self.bus = bus
        self.document_store = document_store
        self.vector_index = vector_index
        self.processed_event_ids: set[str] = set()

    def register(self) -> None:
        # Module ownership by topic:
        # upload -> inference -> annotation -> embedding -> query.
        self.bus.subscribe(Topic.IMAGE_SUBMITTED, self._on_image_submitted)
        self.bus.subscribe(Topic.INFERENCE_COMPLETED, self._on_inference_completed)
        self.bus.subscribe(Topic.ANNOTATION_STORED, self._on_annotation_stored)
        self.bus.subscribe(Topic.ANNOTATION_CORRECTED, self._on_annotation_corrected)
        self.bus.subscribe(Topic.QUERY_SUBMITTED, self._on_query_submitted)

    def _once(self, event: EventEnvelope) -> bool:
        # Idempotency guard: duplicate event IDs are ignored.
        if event.event_id in self.processed_event_ids:
            return False
        self.processed_event_ids.add(event.event_id)
        return True

    def _on_image_submitted(self, event: EventEnvelope) -> None:
        if not self._once(event):
            return
        image_id = event.payload["image_id"]
        objects = [{"label": "object", "confidence": 0.95, "bbox": [0, 0, 10, 10]}]
        self.bus.publish(
            EventEnvelope.create(
                Topic.INFERENCE_COMPLETED,
                {
                    "image_id": image_id,
                    "model_version": "v0",
                    "objects": objects,
                },
            )
        )

    def _on_inference_completed(self, event: EventEnvelope) -> None:
        if not self._once(event):
            return
        image_id = event.payload["image_id"]
        annotation_id = f"ann-{image_id}"
        objects = event.payload["objects"]
        self.document_store.upsert_annotation(image_id, annotation_id, objects)
        self.bus.publish(
            EventEnvelope.create(
                Topic.ANNOTATION_STORED,
                {
                    "image_id": image_id,
                    "annotation_id": annotation_id,
                    "objects": objects,
                    "source_event_id": event.event_id,
                },
            )
        )

    def _on_annotation_stored(self, event: EventEnvelope) -> None:
        if not self._once(event):
            return
        image_id = event.payload["image_id"]
        # Deterministic placeholder embedding for testable behavior.
        vector = [float((ord(c) % 10) / 10.0) for c in image_id][:8] or [0.0]
        self.vector_index.add(image_id, vector)
        self.bus.publish(
            EventEnvelope.create(
                Topic.EMBEDDING_CREATED,
                {
                    "image_id": image_id,
                    "vector_id": f"vec-{image_id}",
                    "dimensions": len(vector),
                },
            )
        )

    def _on_annotation_corrected(self, event: EventEnvelope) -> None:
        if not self._once(event):
            return
        image_id = event.payload["image_id"]
        annotation_id = event.payload["annotation_id"]
        base = self.document_store.records.get(image_id, {"objects": []})
        corrected_objects = base["objects"] + event.payload["corrections"]
        self.document_store.upsert_annotation(image_id, annotation_id, corrected_objects)
        self.bus.publish(
            EventEnvelope.create(
                Topic.ANNOTATION_STORED,
                {
                    "image_id": image_id,
                    "annotation_id": annotation_id,
                    "objects": corrected_objects,
                    "source_event_id": event.event_id,
                },
            )
        )

    def _on_query_submitted(self, event: EventEnvelope) -> None:
        if not self._once(event):
            return
        query_id = event.payload["query_id"]
        text = event.payload["text"]
        top_k = event.payload["top_k"]
        results = self.vector_index.search(text, top_k)
        # Query completion is published so CLI can stay decoupled from storage.
        self.bus.publish(
            EventEnvelope.create(
                Topic.QUERY_COMPLETED,
                {
                    "query_id": query_id,
                    "results": results,
                },
            )
        )
