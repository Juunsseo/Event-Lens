from __future__ import annotations

from event_lens.config import Settings
from event_lens.services.document_db import InMemoryDocumentStore, MongoDocumentStore
from event_lens.services.embedding import EmbeddingService
from event_lens.services.vector_index import FaissVectorIndex, InMemoryVectorIndex


def build_document_store(settings: Settings):
    if settings.use_mongo:
        return MongoDocumentStore(
            settings.mongo_uri,
            database=settings.mongo_database,
            collection=settings.mongo_collection,
        )
    return InMemoryDocumentStore()


def build_embedding_service(settings: Settings) -> EmbeddingService:
    return EmbeddingService(dimensions=settings.embedding_dimensions)


def build_vector_index(settings: Settings):
    if settings.use_faiss:
        return FaissVectorIndex(
            dimensions=settings.embedding_dimensions,
            index_path=settings.faiss_index_path,
            labels_path=settings.faiss_labels_path,
        )
    return InMemoryVectorIndex()
