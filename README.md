# EventLens

[![EventLens](http://img.youtube.com/vi/Do2oT4kDuxs/0.jpg)](http://www.youtube.com/watch?v=Do2oT4kDuxs)
Click the thumbnail to pipeline explanation. Recommend using closed caption.

EventLens is an event-driven image annotation and retrieval system. It accepts image submissions, runs inference, stores annotations, builds embeddings, and answers similarity-style queries through strict message contracts.

The default development path runs locally with in-memory storage. Optional adapters add Redis pub/sub, MongoDB persistence, OpenAI-backed image inference, and FAISS vector search.

## Quick Start

Install the package in editable mode with test dependencies:

```bash
python3 -m pip install -e '.[dev]'
```

Run the test suite:

```bash
python3 -m pytest -q
```

Run a local in-memory demo with a local image:

```bash
event-lens demo --image ./sample.jpg --query "find a similar image"
```

Install the optional integration dependencies when using OpenAI, MongoDB, or FAISS:

```bash
python3 -m pip install -e '.[dev,integrations]'
```

## How It Works

The pipeline is organized around topic-based events:

```text
image.submitted
  -> inference.completed
  -> annotation.stored
  -> embedding.created

query.submitted
  -> query.completed
```

Corrections can be published with `annotation.corrected`; the pipeline updates the stored annotation and re-indexes the image.

Each message uses the same envelope shape:

```json
{
  "topic": "image.submitted",
  "event_id": "uuid",
  "timestamp": "ISO-8601 UTC",
  "payload": {}
}
```

Payload contracts are validated in `event_lens/events.py`:

| Topic | Required payload fields |
| --- | --- |
| `image.submitted` | `image_id`, `image_uri`, `submitted_by` |
| `inference.completed` | `image_id`, `model_version`, `objects[]` |
| `annotation.stored` | `image_id`, `annotation_id`, `objects[]`, `source_event_id` |
| `embedding.created` | `image_id`, `vector_id`, `dimensions` |
| `annotation.corrected` | `image_id`, `annotation_id`, `corrections[]` |
| `query.submitted` | `query_id`, `text`, `top_k` |
| `query.completed` | `query_id`, `results[]` |

## Project Layout

```text
event_lens/
  bus.py               # In-memory and Redis pub/sub implementations
  cli.py               # event-lens command-line interface
  config.py            # Environment-based runtime settings
  events.py            # Topics, envelopes, and payload validation
  factory.py           # Runtime component selection
  services/
    pipeline.py        # Event handlers for the end-to-end flow
    inference.py       # Metadata, OpenAI, and hybrid inference
    document_db.py     # In-memory and MongoDB annotation stores
    embedding.py       # Deterministic embedding generation
    vector_index.py    # In-memory and FAISS vector indexes
tests/                 # Unit, system, and optional integration tests
docs/                  # Redis, MongoDB, FAISS, and project status notes
```

## CLI Usage

Start a Redis-backed worker:

```bash
event-lens worker \
  --bus redis \
  --redis-url redis://localhost:6379/0 \
  --inference metadata
```

Submit an image:

```bash
event-lens submit-image \
  --image-id img-1 \
  --image-uri file:///abs/path/image.jpg \
  --submitted-by cli
```

Submit a query:

```bash
event-lens submit-query \
  --query-id q-1 \
  --text "red car" \
  --top-k 5
```

Listen to a topic:

```bash
event-lens listen --topic query.completed
```

Use OpenAI-backed inference by setting `OPENAI_API_KEY` and selecting `--inference openai` or `--inference hybrid`.

## Configuration

Runtime settings are loaded from environment variables. See `.env.example` for the full list.

| Variable | Default | Purpose |
| --- | --- | --- |
| `EVENT_LENS_REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `EVENT_LENS_USE_MONGO` | `false` | Use MongoDB instead of in-memory annotation storage |
| `EVENT_LENS_MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection string |
| `EVENT_LENS_USE_FAISS` | `false` | Use FAISS instead of the in-memory vector index |
| `EVENT_LENS_EMBEDDING_DIMENSIONS` | `16` | Embedding vector size |
| `EVENT_LENS_OPENAI_MODEL` | `gpt-4.1-mini` | OpenAI vision model for inference |
| `OPENAI_API_KEY` | empty | Required for OpenAI inference |

## Optional Smoke Tests

Redis:

```bash
export EVENT_LENS_REDIS_URL="redis://username:password@host:port/0"
export EVENT_LENS_RUN_INTEGRATION_TESTS=1
python3 -m pytest tests/test_redis_integration.py -q
```

MongoDB:

```bash
export EVENT_LENS_MONGO_URI="mongodb+srv://username:password@cluster.example.mongodb.net/?retryWrites=true&w=majority"
export EVENT_LENS_RUN_INTEGRATION_TESTS=1
python3 -m pytest tests/test_mongo_integration.py -q
```

FAISS:

```bash
python3 -m pip install -e '.[dev,integrations]'
python3 -m pytest tests/test_faiss_smoke.py -q
```

More detailed notes live in:

- `docs/REDIS_SMOKE_TEST.md`
- `docs/MONGO_SMOKE_TEST.md`
- `docs/FAISS_SMOKE_TEST.md`
- `docs/STATUS.md`
