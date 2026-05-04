# MongoDB Smoke Test

MongoDB support is verified by a live document round trip.

## Run

```bash
export EVENT_LENS_MONGO_URI="mongodb+srv://username:password@cluster.example.mongodb.net/?retryWrites=true&w=majority"
export EVENT_LENS_MONGO_DATABASE="event_lens_test"
export EVENT_LENS_MONGO_COLLECTION="annotations_test"
export EVENT_LENS_RUN_INTEGRATION_TESTS=1
python3 -m pytest tests/test_mongo_integration.py -q
```

The test connects to MongoDB, pings the server, upserts one annotation document, reads it back, verifies the object fields, and deletes the smoke-test document.

## Expected Result

```text
1 passed
```

If `EVENT_LENS_MONGO_URI` or `EVENT_LENS_RUN_INTEGRATION_TESTS` is missing, the test is skipped so local unit tests remain deterministic.
