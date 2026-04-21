from __future__ import annotations

from event_lens.messaging.bus import MessageBus
from event_lens.schemas.events import EventEnvelope
from event_lens.schemas.topics import Topic
from event_lens.services.document_db import InMemoryDocumentStore
from event_lens.services.embedding import EmbeddingService
from event_lens.services.inference import ImageInferenceService
from event_lens.services.vector_index import InMemoryVectorIndex


class EventPipeline:
    def __init__(
        self,
        bus: MessageBus,
        document_store: InMemoryDocumentStore | None = None,
        vector_index: InMemoryVectorIndex | None = None,
        inference_service: ImageInferenceService | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self.bus = bus
        self.document_store = document_store or InMemoryDocumentStore()
        self.vector_index = vector_index or InMemoryVectorIndex()
        self.inference_service = inference_service or ImageInferenceService()
        self.embedding_service = embedding_service or EmbeddingService(dimensions=16)
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
        image_uri = event.payload["image_uri"]
        inference = self.inference_service.infer(image_uri)
        self.bus.publish(
            EventEnvelope.create(
                Topic.INFERENCE_COMPLETED,
                {
                    "image_id": image_id,
                    "model_version": inference.model_version,
                    "objects": inference.objects,
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
        vector = self.embedding_service.create_embedding(image_id, event.payload["objects"])
        vector_id = self.vector_index.add(image_id, vector)
        self.bus.publish(
            EventEnvelope.create(
                Topic.EMBEDDING_CREATED,
                {
                    "image_id": image_id,
                    "vector_id": vector_id,
                    "dimensions": len(vector),
                },
            )
        )

    def _on_annotation_corrected(self, event: EventEnvelope) -> None:
        if not self._once(event):
            return
        image_id = event.payload["image_id"]
        annotation_id = event.payload["annotation_id"]
        base = self.document_store.get_annotation(image_id) or {"objects": []}
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
        query_vector = self.embedding_service.create_embedding(image_id=f"query:{query_id}", objects=[{"text": text}])
        results = self.vector_index.search(query_vector, top_k)
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
