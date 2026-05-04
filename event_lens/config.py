from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    redis_url: str = "redis://localhost:6379/0"
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_database: str = "event_lens"
    mongo_collection: str = "annotations"
    openai_model: str = "gpt-4.1-mini"
    embedding_dimensions: int = 16
    faiss_index_path: str = "data/faiss.index"
    faiss_labels_path: str = "data/faiss_labels.json"
    use_mongo: bool = False
    use_faiss: bool = False


def load_settings() -> Settings:
    return Settings(
        redis_url=os.getenv("EVENT_LENS_REDIS_URL", Settings.redis_url),
        mongo_uri=os.getenv("EVENT_LENS_MONGO_URI", Settings.mongo_uri),
        mongo_database=os.getenv("EVENT_LENS_MONGO_DATABASE", Settings.mongo_database),
        mongo_collection=os.getenv("EVENT_LENS_MONGO_COLLECTION", Settings.mongo_collection),
        openai_model=os.getenv("EVENT_LENS_OPENAI_MODEL", Settings.openai_model),
        embedding_dimensions=int(os.getenv("EVENT_LENS_EMBEDDING_DIMENSIONS", Settings.embedding_dimensions)),
        faiss_index_path=os.getenv("EVENT_LENS_FAISS_INDEX_PATH", Settings.faiss_index_path),
        faiss_labels_path=os.getenv("EVENT_LENS_FAISS_LABELS_PATH", Settings.faiss_labels_path),
        use_mongo=_env_bool("EVENT_LENS_USE_MONGO"),
        use_faiss=_env_bool("EVENT_LENS_USE_FAISS"),
    )


def _env_bool(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}
