# EventLens

Event-driven image annotation and retrieval system with strict message contracts and Redis topic transport.

## Project Structure

```text
event_lens/
  messaging/
    bus.py           # In-memory deterministic pub/sub for unit tests
    redis_bus.py     # Redis pub/sub transport (topics + JSON envelopes)
  schemas/
    topics.py        # Canonical topic names
    events.py        # Event envelope contract
    messages.py      # Topic-specific payload contracts
  services/
    pipeline.py      # Upload -> inference -> annotation -> embedding -> query flow
tests/
  test_events.py
  test_message_contracts.py
  test_pipeline_system.py
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

## Testing

The test suite covers:

- Envelope validation and serialization.
- Unit tests for all topic payload contracts.
- End-to-end event-driven flow.
- Idempotency for duplicate event IDs.
- Malformed message dead-letter handling.
- Annotation correction update + re-indexing path.

Run tests:

```bash
python3 -m pytest -q
```
