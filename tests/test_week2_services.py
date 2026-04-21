import base64

from event_lens.services.embedding import EmbeddingService
from event_lens.services.inference import ImageInferenceService
from event_lens.services.vector_index import InMemoryVectorIndex


def _write_test_png(tmp_path, name: str = "test.png") -> str:
    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
    )
    image_path = tmp_path / name
    image_path.write_bytes(png_bytes)
    return image_path.as_uri()


def test_image_inference_service_returns_objects(tmp_path) -> None:
    service = ImageInferenceService()
    output = service.infer(_write_test_png(tmp_path))

    assert output.model_version.startswith("v1")
    assert len(output.objects) >= 1
    assert output.objects[0]["label"] == "image"


def test_embedding_service_dimensions_stable() -> None:
    service = EmbeddingService(dimensions=12)
    vector1 = service.create_embedding("img-1", [{"label": "car"}])
    vector2 = service.create_embedding("img-1", [{"label": "car"}])

    assert len(vector1) == 12
    assert vector1 == vector2


def test_in_memory_vector_index_search_orders_by_similarity() -> None:
    index = InMemoryVectorIndex()
    index.add("img-close", [1.0, 0.0])
    index.add("img-far", [0.0, 1.0])

    results = index.search([1.0, 0.0], top_k=2)
    assert results[0]["image_id"] == "img-close"
    assert results[0]["score"] >= results[1]["score"]
