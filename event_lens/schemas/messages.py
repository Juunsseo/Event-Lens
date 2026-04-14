from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .topics import Topic


class MessageValidationError(ValueError):
    """Raised when a message payload is invalid for its topic."""


@dataclass(frozen=True)
class ImageSubmitted:
    image_id: str
    image_uri: str
    submitted_by: str


@dataclass(frozen=True)
class InferenceCompleted:
    image_id: str
    model_version: str
    objects: list[dict[str, Any]]


@dataclass(frozen=True)
class AnnotationStored:
    image_id: str
    annotation_id: str
    objects: list[dict[str, Any]]
    source_event_id: str


@dataclass(frozen=True)
class EmbeddingCreated:
    image_id: str
    vector_id: str
    dimensions: int


@dataclass(frozen=True)
class AnnotationCorrected:
    image_id: str
    annotation_id: str
    corrections: list[dict[str, Any]]


@dataclass(frozen=True)
class QuerySubmitted:
    query_id: str
    text: str
    top_k: int


@dataclass(frozen=True)
class QueryCompleted:
    query_id: str
    results: list[dict[str, Any]]


def _require_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise MessageValidationError(f"'{key}' must be a non-empty string")
    return value


def _require_int(payload: dict[str, Any], key: str, *, minimum: int | None = None) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        raise MessageValidationError(f"'{key}' must be an integer")
    if minimum is not None and value < minimum:
        raise MessageValidationError(f"'{key}' must be >= {minimum}")
    return value


def _require_list(payload: dict[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise MessageValidationError(f"'{key}' must be a list")
    return value


def validate_payload(topic: Topic, payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise MessageValidationError("payload must be a dictionary")

    if topic == Topic.IMAGE_SUBMITTED:
        ImageSubmitted(
            image_id=_require_str(payload, "image_id"),
            image_uri=_require_str(payload, "image_uri"),
            submitted_by=_require_str(payload, "submitted_by"),
        )
    elif topic == Topic.INFERENCE_COMPLETED:
        InferenceCompleted(
            image_id=_require_str(payload, "image_id"),
            model_version=_require_str(payload, "model_version"),
            objects=_require_list(payload, "objects"),
        )
    elif topic == Topic.ANNOTATION_STORED:
        AnnotationStored(
            image_id=_require_str(payload, "image_id"),
            annotation_id=_require_str(payload, "annotation_id"),
            objects=_require_list(payload, "objects"),
            source_event_id=_require_str(payload, "source_event_id"),
        )
    elif topic == Topic.EMBEDDING_CREATED:
        EmbeddingCreated(
            image_id=_require_str(payload, "image_id"),
            vector_id=_require_str(payload, "vector_id"),
            dimensions=_require_int(payload, "dimensions", minimum=1),
        )
    elif topic == Topic.ANNOTATION_CORRECTED:
        AnnotationCorrected(
            image_id=_require_str(payload, "image_id"),
            annotation_id=_require_str(payload, "annotation_id"),
            corrections=_require_list(payload, "corrections"),
        )
    elif topic == Topic.QUERY_SUBMITTED:
        QuerySubmitted(
            query_id=_require_str(payload, "query_id"),
            text=_require_str(payload, "text"),
            top_k=_require_int(payload, "top_k", minimum=1),
        )
    elif topic == Topic.QUERY_COMPLETED:
        QueryCompleted(
            query_id=_require_str(payload, "query_id"),
            results=_require_list(payload, "results"),
        )
    else:
        raise MessageValidationError(f"unsupported topic: {topic}")
