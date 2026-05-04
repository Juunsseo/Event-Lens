import importlib.util

import pytest

from event_lens.services.vector_index import FaissVectorIndex


pytestmark = pytest.mark.integration


def test_faiss_index_search_and_persistence(tmp_path) -> None:
    if importlib.util.find_spec("faiss") is None:
        pytest.skip("install faiss-cpu to run FAISS smoke test")

    index_path = tmp_path / "faiss.index"
    labels_path = tmp_path / "labels.json"
    index = FaissVectorIndex(dimensions=2, index_path=str(index_path), labels_path=str(labels_path))

    index.add("img-close", [1.0, 0.0])
    index.add("img-far", [0.0, 1.0])
    results = index.search([1.0, 0.0], top_k=2)

    assert results[0]["image_id"] == "img-close"

    index.save()
    restored = FaissVectorIndex(dimensions=2, index_path=str(index_path), labels_path=str(labels_path))
    restored_results = restored.search([1.0, 0.0], top_k=2)

    assert restored_results[0]["image_id"] == "img-close"
    assert len(restored_results) == 2
