# EventLens

Event-driven image annotation and retrieval system.

## Overview

This project builds a modular image-processing pipeline using pub-sub messaging.  
Images are submitted as events, processed by services, stored in a document database, and indexed for similarity search.

The focus is on **architecture, modular design, and testing**, not model training.

## Components

- CLI Service
- Image Service
- Inference Service
- Document DB Service
- Embedding Service
- Vector Index Service
- Messaging Layer
- Event Generator

## Event Topics

- `image.submitted`
- `inference.completed`
- `annotation.stored`
- `embedding.created`
- `annotation.corrected`
- `query.submitted`
- `query.completed`

## Design Rules

- Services communicate through events
- Each datastore is owned by one service only
- CLI does not access databases directly
- System must be modular and testable

## Testing Goals

- Idempotency
- Robustness
- Eventual consistency
- Accurate queries

Failure cases include duplicate, dropped, delayed events, and subscriber downtime.

## Tech Stack

- Redis Pub-Sub
- Document DB
- FAISS

## Notes

- Do not train models
- Do not implement ANN algorithms
- Focus on system integration and testing
