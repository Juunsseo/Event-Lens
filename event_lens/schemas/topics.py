from enum import Enum


class Topic(str, Enum):
    IMAGE_SUBMITTED = "image.submitted"
    INFERENCE_COMPLETED = "inference.completed"
    ANNOTATION_STORED = "annotation.stored"
    EMBEDDING_CREATED = "embedding.created"
    ANNOTATION_CORRECTED = "annotation.corrected"
    QUERY_SUBMITTED = "query.submitted"
    QUERY_COMPLETED = "query.completed"
