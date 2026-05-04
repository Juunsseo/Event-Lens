from __future__ import annotations

import argparse
import json
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Callable

from event_lens.config import load_settings
from event_lens.factory import build_document_store, build_embedding_service, build_vector_index
from event_lens.bus import InMemoryBus, MessageBus
from event_lens.bus import RedisBus
from event_lens.events import EventEnvelope
from event_lens.events import Topic
from event_lens.services.inference import HybridInferenceService, ImageInferenceService, OpenAIImageInferenceService
from event_lens.services.pipeline import EventPipeline


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    handlers: dict[str, Callable[[argparse.Namespace], int]] = {
        "worker": _cmd_worker,
        "submit-image": _cmd_submit_image,
        "submit-query": _cmd_submit_query,
        "listen": _cmd_listen,
        "demo": _cmd_demo,
    }

    return handlers[args.command](args)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="EventLens CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    worker = sub.add_parser("worker", help="Run event processing worker")
    _add_common_bus_args(worker)
    _add_inference_args(worker)

    submit_image = sub.add_parser("submit-image", help="Publish image.submitted event")
    _add_common_bus_args(submit_image)
    submit_image.add_argument("--image-id", required=True)
    submit_image.add_argument("--image-uri", required=True)
    submit_image.add_argument("--submitted-by", default="cli")

    submit_query = sub.add_parser("submit-query", help="Publish query.submitted event")
    _add_common_bus_args(submit_query)
    submit_query.add_argument("--query-id", required=True)
    submit_query.add_argument("--text", required=True)
    submit_query.add_argument("--top-k", type=int, default=5)

    listen = sub.add_parser("listen", help="Listen and print events for a topic")
    _add_common_bus_args(listen)
    listen.add_argument("--topic", required=True, choices=[t.value for t in Topic])

    demo = sub.add_parser("demo", help="Run local in-memory submit+query demo")
    demo.add_argument("--image", required=True, help="Path to local image file")
    demo.add_argument("--query", required=True)
    _add_inference_args(demo)

    return parser


def _add_common_bus_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--bus", choices=["redis", "memory"], default="redis")
    parser.add_argument("--redis-url", default=None)


def _add_inference_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--inference", choices=["metadata", "openai", "hybrid"], default="metadata")
    parser.add_argument("--openai-model", default=None)


def _build_bus(bus_kind: str, redis_url: str) -> MessageBus:
    if bus_kind == "memory":
        return InMemoryBus()
    return RedisBus(redis_url=redis_url)


def _build_inference_service(kind: str, model: str):
    if kind == "metadata":
        return ImageInferenceService()
    if kind == "openai":
        return OpenAIImageInferenceService(model=model)
    return HybridInferenceService(primary=OpenAIImageInferenceService(model=model), fallback=ImageInferenceService())


def _cmd_worker(args: argparse.Namespace) -> int:
    settings = load_settings()
    bus = _build_bus(args.bus, args.redis_url or settings.redis_url)
    pipeline = EventPipeline(
        bus=bus,
        document_store=build_document_store(settings),
        vector_index=build_vector_index(settings),
        inference_service=_build_inference_service(args.inference, args.openai_model or settings.openai_model),
        embedding_service=build_embedding_service(settings),
    )
    pipeline.register()

    if isinstance(bus, RedisBus):
        bus.start()

    print("worker started; press Ctrl+C to stop")
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        if isinstance(bus, RedisBus):
            bus.stop()
    return 0


def _cmd_submit_image(args: argparse.Namespace) -> int:
    settings = load_settings()
    bus = _build_bus(args.bus, args.redis_url or settings.redis_url)
    if isinstance(bus, InMemoryBus):
        # In-memory mode executes a full local flow in one command.
        pipeline = EventPipeline(bus=bus)
        pipeline.register()

    event = EventEnvelope.create(
        Topic.IMAGE_SUBMITTED,
        {
            "image_id": args.image_id,
            "image_uri": args.image_uri,
            "submitted_by": args.submitted_by,
        },
    )
    bus.publish(event)
    print(json.dumps(event.to_dict(), indent=2))
    return 0


def _cmd_submit_query(args: argparse.Namespace) -> int:
    settings = load_settings()
    bus = _build_bus(args.bus, args.redis_url or settings.redis_url)
    done = threading.Event()
    results_holder: list[dict] = []

    if isinstance(bus, InMemoryBus):
        pipeline = EventPipeline(bus=bus)
        pipeline.register()

    bus.subscribe(Topic.QUERY_COMPLETED, lambda e: _capture_result(e, args.query_id, done, results_holder))
    if isinstance(bus, RedisBus):
        bus.start()

    event = EventEnvelope.create(
        Topic.QUERY_SUBMITTED,
        {
            "query_id": args.query_id,
            "text": args.text,
            "top_k": args.top_k,
        },
    )
    bus.publish(event)

    done.wait(timeout=2)
    if isinstance(bus, RedisBus):
        bus.stop()

    if results_holder:
        print(json.dumps(results_holder[-1], indent=2))
    else:
        print(json.dumps(event.to_dict(), indent=2))
    return 0


def _cmd_listen(args: argparse.Namespace) -> int:
    settings = load_settings()
    bus = _build_bus(args.bus, args.redis_url or settings.redis_url)
    topic = Topic(args.topic)

    def _printer(event: EventEnvelope) -> None:
        print(json.dumps(event.to_dict(), indent=2), flush=True)

    bus.subscribe(topic, _printer)

    if isinstance(bus, InMemoryBus):
        print("listen requires redis bus to receive external events")
        return 1

    bus.start()
    stop = threading.Event()

    def _handle_signal(_sig, _frame):
        stop.set()

    signal.signal(signal.SIGINT, _handle_signal)
    print(f"listening on {topic.value}; press Ctrl+C to stop")
    while not stop.is_set():
        time.sleep(0.5)

    bus.stop()
    return 0


def _cmd_demo(args: argparse.Namespace) -> int:
    settings = load_settings()
    bus = InMemoryBus()
    pipeline = EventPipeline(
        bus=bus,
        inference_service=_build_inference_service(args.inference, args.openai_model or settings.openai_model),
        embedding_service=build_embedding_service(settings),
    )
    pipeline.register()

    completed: list[dict] = []
    bus.subscribe(Topic.QUERY_COMPLETED, lambda e: completed.append(e.to_dict()))

    image_path = Path(args.image).expanduser().resolve()
    image_id = image_path.stem
    bus.publish(
        EventEnvelope.create(
            Topic.IMAGE_SUBMITTED,
            {
                "image_id": image_id,
                "image_uri": image_path.as_uri(),
                "submitted_by": "cli-demo",
            },
        )
    )
    bus.publish(
        EventEnvelope.create(
            Topic.QUERY_SUBMITTED,
            {
                "query_id": f"q-{int(time.time())}",
                "text": args.query,
                "top_k": 3,
            },
        )
    )

    if not completed:
        print("no query.completed event received", file=sys.stderr)
        return 1

    print(json.dumps(completed[-1], indent=2))
    return 0


def _capture_result(event: EventEnvelope, query_id: str, done: threading.Event, sink: list[dict]) -> None:
    if event.payload.get("query_id") != query_id:
        return
    sink.append(event.to_dict())
    done.set()


if __name__ == "__main__":
    raise SystemExit(main())
