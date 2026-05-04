# FAISS Smoke Test

FAISS support is verified by an add/search/save/load round trip.

## Run

```bash
python3 -m pip install -e '.[dev,integrations]'
python3 -m pytest tests/test_faiss_smoke.py -q
```

The test builds a FAISS index, inserts two vectors, searches for the closest vector, saves the index and labels to disk, reloads them, and searches again.

## Runtime Settings

```bash
export EVENT_LENS_USE_FAISS=true
export EVENT_LENS_EMBEDDING_DIMENSIONS=16
export EVENT_LENS_FAISS_INDEX_PATH=data/faiss.index
export EVENT_LENS_FAISS_LABELS_PATH=data/faiss_labels.json
```

When `EVENT_LENS_USE_FAISS=true`, the worker selects `FaissVectorIndex` through `event_lens.factory.build_vector_index()`.

If `faiss-cpu` is not installed, the smoke test is skipped.
