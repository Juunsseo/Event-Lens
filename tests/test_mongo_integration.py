import os

import pytest

from event_lens.services.document_db import MongoDocumentStore


pytestmark = pytest.mark.integration


def _mongo_settings() -> tuple[str, str, str]:
    uri = os.getenv("EVENT_LENS_MONGO_URI")
    if not uri:
        pytest.skip("set EVENT_LENS_MONGO_URI to run live MongoDB integration tests")
    if os.getenv("EVENT_LENS_RUN_INTEGRATION_TESTS") != "1":
        pytest.skip("set EVENT_LENS_RUN_INTEGRATION_TESTS=1 to run live integration tests")
    database = os.getenv("EVENT_LENS_MONGO_DATABASE", "event_lens_test")
    collection = os.getenv("EVENT_LENS_MONGO_COLLECTION", "annotations_test")
    return uri, database, collection


def test_online_mongodb_annotation_round_trip() -> None:
    uri, database, collection = _mongo_settings()
    store = MongoDocumentStore(uri, database=database, collection=collection)
    image_id = "mongo-smoke-test-image"
    objects = [{"label": "whole_image", "confidence": 1.0, "bbox": [0, 0, 1, 1]}]

    try:
        assert store.ping() is True
        store.upsert_annotation(image_id, "ann-mongo-smoke-test", objects)
        stored = store.get_annotation(image_id)

        assert stored is not None
        assert stored["image_id"] == image_id
        assert stored["annotation_id"] == "ann-mongo-smoke-test"
        assert stored["objects"] == objects
    finally:
        store.delete_annotation(image_id)
