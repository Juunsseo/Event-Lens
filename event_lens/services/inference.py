from __future__ import annotations

import base64
import json
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen


@dataclass(frozen=True)
class InferenceOutput:
    model_version: str
    objects: list[dict]


class ImageInferenceService:
    """Deterministic local inference based on image metadata."""

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


class OpenAIImageInferenceService:
    """Image inference backed by OpenAI vision-capable models."""

    def __init__(self, model: str = "gpt-4.1-mini", api_key: str | None = None) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - optional runtime dependency
            raise RuntimeError("openai package is required for OpenAIImageInferenceService") from exc

        self.model = model
        self._client = OpenAI(api_key=api_key)

    def infer(self, image_uri: str) -> InferenceOutput:
        image_url = self._to_model_image_url(image_uri)
        instructions = (
            "Analyze this image and return strict JSON with top-level key 'objects'. "
            "Each object must contain: label (string), confidence (0..1 number), "
            "bbox ([x1,y1,x2,y2] integers), attributes (object). "
            "Return JSON only."
        )

        response = self._client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": instructions},
                        {"type": "input_image", "image_url": image_url},
                    ],
                }
            ],
            temperature=0,
        )

        payload = _extract_json_payload(_response_text(response))
        objects = payload.get("objects")
        if not isinstance(objects, list):
            raise ValueError("OpenAI response must include an 'objects' list")

        return InferenceOutput(model_version=f"openai:{self.model}", objects=objects)

    def _to_model_image_url(self, image_uri: str) -> str:
        parsed = urlparse(image_uri)
        if parsed.scheme in {"http", "https"}:
            return image_uri

        if parsed.scheme == "file":
            path = Path(parsed.path)
        else:
            path = Path(image_uri)

        mime_type = mimetypes.guess_type(path.name)[0] or "image/png"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"


class HybridInferenceService:
    """Try OpenAI first; fallback to metadata-based inference on errors."""

    def __init__(self, primary: OpenAIImageInferenceService, fallback: ImageInferenceService | None = None) -> None:
        self.primary = primary
        self.fallback = fallback or ImageInferenceService()

    def infer(self, image_uri: str) -> InferenceOutput:
        try:
            return self.primary.infer(image_uri)
        except Exception:
            return self.fallback.infer(image_uri)


def _response_text(response: object) -> str:
    text = getattr(response, "output_text", None)
    if isinstance(text, str) and text.strip():
        return text

    output = getattr(response, "output", None)
    if isinstance(output, list):
        parts: list[str] = []
        for item in output:
            content = getattr(item, "content", None)
            if not isinstance(content, list):
                continue
            for chunk in content:
                chunk_text = getattr(chunk, "text", None)
                if isinstance(chunk_text, str):
                    parts.append(chunk_text)
        if parts:
            return "\n".join(parts)

    raise ValueError("OpenAI response did not include text output")


def _extract_json_payload(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or start >= end:
        raise ValueError("model response did not include JSON object")

    return json.loads(cleaned[start : end + 1])
