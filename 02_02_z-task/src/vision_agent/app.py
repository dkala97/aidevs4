#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any

from redis.asyncio import Redis

from src.agent import run
from src.shared_config import PROJECT_ROOT

DEFAULT_CHANNEL = "vision:request"
DONE_CHANNEL = "vision:done"
DEFAULT_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DEFAULT_PROMPT_PATH = PROJECT_ROOT / "vision_prompt.md"
DEFAULT_PROMPT_FALLBACK = "Describe the image in detail."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Redis-driven vision worker."
    )
    parser.add_argument(
        "--redis-url",
        default=DEFAULT_REDIS_URL,
        help="Redis connection URL.",
    )
    parser.add_argument(
        "--channel",
        default=DEFAULT_CHANNEL,
        help="Redis channel name to subscribe to.",
    )
    parser.add_argument(
        "--default-prompt-path",
        default=str(DEFAULT_PROMPT_PATH),
        help="Path to the default prompt file.",
    )
    parser.add_argument(
        "--query",
        default=None,
        help="Default prompt/query",
    )
    return parser.parse_args()


def _load_default_prompt(default_prompt_path: str) -> str:
    requested_path = Path(default_prompt_path)
    prompt_path = requested_path if requested_path.is_absolute() else (PROJECT_ROOT / requested_path)
    prompt_path = prompt_path.resolve()
    if prompt_path.is_file():
        prompt = prompt_path.read_text(encoding="utf-8").strip()
        if prompt:
            return prompt

    return DEFAULT_PROMPT_FALLBACK


def _extract_image_path(payload: str) -> str:
    text = payload.strip()
    return text


def _resolve_prompt_for_image(image_path: str, default_prompt: str) -> str:
    image_full_path = (PROJECT_ROOT / image_path).resolve()
    sidecar_path = image_full_path.with_name(f"{image_full_path.stem}-prompt.md")

    if sidecar_path.is_file():
        sidecar_prompt = sidecar_path.read_text(encoding="utf-8").strip()
        if sidecar_prompt:
            return sidecar_prompt

    return default_prompt

def _write_info(image_path: str, result_info):
    image_full_path = (PROJECT_ROOT / image_path).resolve()
    info_path = image_full_path.with_name(f"{image_full_path.stem}-info.md")
    info_path.write_text(f"{result_info.strip()}\n", encoding="utf-8")

async def async_main() -> int:
    args = parse_args()
    redis_client: Redis | None = None
    pubsub: Any = None
    default_prompt = args.query
    if not default_prompt:
        default_prompt = _load_default_prompt(args.default_prompt_path)

    try:
        print(f"Subscribing to {args.channel} on {args.redis_url}", flush=True)
        redis_client = Redis.from_url(args.redis_url, decode_responses=True)
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(args.channel)

        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue

            payload = message.get("data")
            if not isinstance(payload, str):
                continue

            try:
                image_path = _extract_image_path(payload)
                print(f"Processing started for image: {image_path}", flush=True)
                prompt = _resolve_prompt_for_image(image_path, default_prompt)
                prompt += f"\nImage path: {image_path}"

                print("Starting agent loop...")
                result = await run(prompt)
                print("Agent finished")

                _write_info(image_path, result["response"])

                print()
                print(result["response"])

                await redis_client.publish(DONE_CHANNEL, image_path)

            except Exception as error:
                print(f"Request failed: {error}", flush=True)

        return 0
    except (RuntimeError, ValueError) as error:
        print(f"Startup error: {error}", flush=True)
        return 1
    finally:
        if pubsub is not None:
            await pubsub.close()
        if redis_client is not None:
            await redis_client.aclose()


def main() -> int:
    try:
        return asyncio.run(async_main())
    except KeyboardInterrupt:
        print("Interrupted", flush=True)
        return 130


if __name__ == "__main__":
    sys.exit(main())