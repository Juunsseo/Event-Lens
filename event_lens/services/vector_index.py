from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path


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
    """FAISS-backed vector index for persistent similarity search."""

    dimensions: int
    index_path: str | None = None
    labels_path: str | None = None
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
        if self.index_path and self.labels_path:
            self.load()

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

    def save(self) -> None:
        if not self.index_path or not self.labels_path:
            raise ValueError("index_path and labels_path are required to save FAISS state")
        index_path = Path(self.index_path)
        labels_path = Path(self.labels_path)
        index_path.parent.mkdir(parents=True, exist_ok=True)
        labels_path.parent.mkdir(parents=True, exist_ok=True)
        self._faiss.write_index(self._index, str(index_path))
        labels_path.write_text(json.dumps(self._labels, indent=2), encoding="utf-8")

    def load(self) -> None:
        index_path = Path(self.index_path or "")
        labels_path = Path(self.labels_path or "")
        if not index_path.exists() or not labels_path.exists():
            return
        self._index = self._faiss.read_index(str(index_path))
        self._labels = json.loads(labels_path.read_text(encoding="utf-8"))
        if self._index.d != self.dimensions:
            raise ValueError(f"FAISS index dimensions {self._index.d} do not match configured {self.dimensions}")


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
