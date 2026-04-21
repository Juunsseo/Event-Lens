from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen


@dataclass(frozen=True)
class InferenceOutput:
    model_version: str
    objects: list[dict]


class ImageInferenceService:
    """Image inference integration point for week-2 service wiring."""

    def __init__(self, model_version: str = "v1-image-metadata") -> None:
        self.model_version = model_version

    def infer(self, image_uri: str) -> InferenceOutput:
        width, height, mode = self._read_image_metadata(image_uri)
        orientation = "landscape" if width >= height else "portrait"
        area = width * height

        objects = [
            {
                "label": "image",
                "confidence": 1.0,
                "bbox": [0, 0, width, height],
                "attributes": {
                    "mode": mode,
                    "orientation": orientation,
                    "area": area,
                },
            }
        ]

        if area > 1_000_000:
            objects.append(
                {
                    "label": "high_resolution",
                    "confidence": 0.9,
                    "bbox": [0, 0, width, height],
                    "attributes": {"threshold": 1_000_000},
                }
            )

        return InferenceOutput(model_version=self.model_version, objects=objects)

    def _read_image_metadata(self, image_uri: str) -> tuple[int, int, str]:
        # Prefer Pillow when available for robust multi-format metadata parsing.
        try:
            from PIL import Image
        except ImportError:
            Image = None

        if Image is not None:
            with self._open_stream(image_uri) as stream:
                with Image.open(stream) as image:
                    width, height = image.size
                    mode = image.mode or "unknown"
                    return int(width), int(height), mode

        # Fallback: infer from file size when Pillow is unavailable.
        size = self._read_size(image_uri)
        width = max(1, int(size**0.5))
        height = max(1, size // width)
        return width, height, "unknown"

    def _read_size(self, image_uri: str) -> int:
        with self._open_stream(image_uri) as stream:
            content = stream.read()
            return len(content)

    def _open_stream(self, image_uri: str):
        parsed = urlparse(image_uri)

        if parsed.scheme in {"http", "https"}:
            return urlopen(image_uri, timeout=5)

        if parsed.scheme == "file":
            path = Path(parsed.path)
        else:
            path = Path(image_uri)

        return path.open("rb")
