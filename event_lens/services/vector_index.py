from __future__ import annotations

import math
from dataclasses import dataclass, field


class InMemoryVectorIndex:
    """Vector index used in tests and local development."""

    def __init__(self) -> None:
        self.vectors: dict[str, list[float]] = {}

    def add(self, image_id: str, vector: list[float]) -> str:
        self.vectors[image_id] = vector
        return f"vec-{image_id}"

    def search(self, query_vector: list[float], top_k: int) -> list[dict[str, float | str]]:
        scores: list[tuple[str, float]] = []
        for image_id, candidate in self.vectors.items():
            scores.append((image_id, _cosine_similarity(query_vector, candidate)))
        scores.sort(key=lambda item: item[1], reverse=True)
        return [{"image_id": image_id, "score": score} for image_id, score in scores[:top_k]]


@dataclass
class FaissVectorIndex:
    """FAISS-backed vector index for week-2 integration."""

    dimensions: int
    _labels: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        try:
            import faiss
            import numpy as np
        except ImportError as exc:  # pragma: no cover - optional runtime dependency
            raise RuntimeError("faiss-cpu and numpy are required for FaissVectorIndex") from exc

        self._faiss = faiss
        self._np = np
        self._index = faiss.IndexFlatIP(self.dimensions)

    def add(self, image_id: str, vector: list[float]) -> str:
        arr = self._np.array([_normalize(vector)], dtype="float32")
        self._index.add(arr)
        self._labels.append(image_id)
        return f"vec-{image_id}-{len(self._labels) - 1}"

    def search(self, query_vector: list[float], top_k: int) -> list[dict[str, float | str]]:
        if self._index.ntotal == 0:
            return []
        query = self._np.array([_normalize(query_vector)], dtype="float32")
        scores, indices = self._index.search(query, top_k)
        results: list[dict[str, float | str]] = []
        for idx, score in zip(indices[0], scores[0]):
            if idx < 0:
                continue
            results.append({"image_id": self._labels[idx], "score": float(score)})
        return results


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return vector
    return [v / norm for v in vector]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        n = min(len(a), len(b))
        a = a[:n]
        b = b[:n]
    an = _normalize(a)
    bn = _normalize(b)
    return float(sum(x * y for x, y in zip(an, bn)))
