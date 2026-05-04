# Redis Smoke Test

Redis support is verified by a live pub/sub round trip.

## Run

```bash
export EVENT_LENS_REDIS_URL="redis://username:password@host:port/0"
export EVENT_LENS_RUN_INTEGRATION_TESTS=1
python3 -m pytest tests/test_redis_integration.py -q
```

The test subscribes to `query.completed`, publishes a JSON event envelope through `RedisBus`, and waits for the same event to arrive through Redis pub/sub.

## Expected Result

```text
1 passed
```

If `EVENT_LENS_REDIS_URL` or `EVENT_LENS_RUN_INTEGRATION_TESTS` is missing, the test is skipped so local unit tests remain deterministic.
