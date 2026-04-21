from __future__ import annotations

import hashlib
import json
from typing import Any


class EmbeddingService:
    """Deterministic embedding service placeholder until production model is wired."""

    def __init__(self, dimensions: int = 16) -> None:
        if dimensions < 1:
            raise ValueError("dimensions must be >= 1")
        self.dimensions = dimensions

    def create_embedding(self, image_id: str, objects: list[dict[str, Any]]) -> list[float]:
        canonical = json.dumps({"image_id": image_id, "objects": objects}, sort_keys=True)
        digest = hashlib.blake2b(canonical.encode("utf-8"), digest_size=64).digest()

        values: list[float] = []
        while len(values) < self.dimensions:
            for byte in digest:
                values.append((byte / 255.0) * 2.0 - 1.0)
                if len(values) == self.dimensions:
                    break
        return values
