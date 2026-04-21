# EventLens

Event-driven image annotation and retrieval system with strict message contracts and Redis topic transport.

## Project Structure

```text
event_lens/
  messaging/
    bus.py              # In-memory deterministic pub/sub for unit tests
    redis_bus.py        # Redis pub/sub transport (topics + JSON envelopes)
  schemas/
    topics.py           # Canonical topic names
    events.py           # Event envelope contract
    messages.py         # Topic-specific payload contracts
  services/
    pipeline.py         # Upload -> inference -> annotation -> embedding -> query flow
    inference.py        # Week-2 image inference service integration
    document_db.py      # Week-2 document DB adapters (in-memory + MongoDB)
    embedding.py        # Week-2 embedding generator service
    vector_index.py     # Week-2 vector index adapters (in-memory + FAISS)
tests/
  test_events.py
  test_message_contracts.py
  test_pipeline_system.py
  test_week2_services.py
```

## Event and Message Definitions

Each event uses one envelope schema:

```json
{
  "topic": "image.submitted",
  "event_id": "uuid",
  "timestamp": "ISO-8601 UTC",
  "payload": {}
}
```

Topic payload contracts:

- `image.submitted`: `image_id`, `image_uri`, `submitted_by`
- `inference.completed`: `image_id`, `model_version`, `objects[]`
- `annotation.stored`: `image_id`, `annotation_id`, `objects[]`, `source_event_id`
- `embedding.created`: `image_id`, `vector_id`, `dimensions`
- `annotation.corrected`: `image_id`, `annotation_id`, `corrections[]`
- `query.submitted`: `query_id`, `text`, `top_k`
- `query.completed`: `query_id`, `results[]`

## Redis Topics and Messaging

- Redis channels are exactly the topic names in `schemas/topics.py`.
- Messages are published as JSON-serialized event envelopes.
- `RedisBus` supports `publish`, `subscribe`, `start`, and `stop`.
- `InMemoryBus` mirrors behavior for deterministic tests and fault-injection (`publish_raw`).

## Week-2 Service Integrations

- Inference: `ImageInferenceService` reads image metadata from local file/HTTP image URIs.
- Document DB: `MongoDocumentStore` adapter available for real MongoDB persistence.
- Embedding: `EmbeddingService` creates deterministic vector embeddings from annotations.
- Vector DB: `FaissVectorIndex` adapter available for real FAISS similarity search.

Install week-2 integrations:

```bash
python3 -m pip install -e '.[dev,week2]'
```

## Testing

The test suite covers:

- Envelope validation and serialization.
- Unit tests for all topic payload contracts.
- End-to-end event-driven flow.
- Idempotency for duplicate event IDs.
- Malformed message dead-letter handling.
- Annotation correction update + re-indexing path.
- Week-2 service behavior for inference, embedding, and vector search.

Run tests:

```bash
python3 -m pytest -q
```
