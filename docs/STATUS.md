# EventLens Status

This document tracks implemented capabilities and the remaining polish items for EventLens.

## Redis Pub/Sub

Status: implemented, with optional live-service verification.

- Redis topic names match the event contract in `event_lens/events.py`.
- `RedisBus` publishes JSON event envelopes and subscribes by topic.
- `InMemoryBus` mirrors the same behavior for deterministic unit tests.
- `tests/test_redis_integration.py` verifies a live Redis pub/sub round trip.
- Run instructions are in `docs/REDIS_SMOKE_TEST.md`.

## MongoDB Document Storage

Status: implemented, with optional live-service verification.

- `MongoDocumentStore` can upsert and fetch annotation documents.
- `.env.example` defines the MongoDB settings.
- CLI/worker settings can select MongoDB with `EVENT_LENS_USE_MONGO=true`.
- `tests/test_mongo_integration.py` verifies a live MongoDB write/read/delete round trip.
- Run instructions are in `docs/MONGO_SMOKE_TEST.md`.

## Image Processing and Embedding

Status: implemented with metadata inference, OpenAI inference, and deterministic embeddings.

- `ImageInferenceService` extracts image metadata.
- `OpenAIImageInferenceService` can use a vision-capable OpenAI model.
- `EmbeddingService` creates deterministic vectors from image/object payloads.
- Next check: add a small fixture image set and document expected annotation output.

## FAISS Vector Search

Status: implemented, with optional dependency verification.

- `InMemoryVectorIndex` supports local similarity search.
- `FaissVectorIndex` supports FAISS nearest-neighbor search when optional deps are installed.
- CLI/worker settings can select FAISS with `EVENT_LENS_USE_FAISS=true`.
- FAISS save/load support is implemented with `EVENT_LENS_FAISS_INDEX_PATH` and `EVENT_LENS_FAISS_LABELS_PATH`.
- `tests/test_faiss_smoke.py` verifies add/search/save/load.
- Run instructions are in `docs/FAISS_SMOKE_TEST.md`.

## Next Steps

1. Add a small fixture image set with expected annotation output.
2. Add a compact end-to-end example that uses Redis, MongoDB, and FAISS together.
