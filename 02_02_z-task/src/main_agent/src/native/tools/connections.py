from __future__ import annotations

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Any

import requests
from redis.asyncio import Redis

from ...config import HUB_URL, HUB_API_KEY, PROJECT_ROOT

REQUEST_CHANNEL = "vision:request"
DONE_CHANNEL = "vision:done"
DEFAULT_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
WAIT_TIMEOUT_SECONDS = 30
logger = logging.getLogger(__name__)


def _truncate(value: str, max_length: int = 300) -> str:
    if len(value) <= max_length:
        return value
    return f"{value[:max_length]}..."


def _log_http_start(method: str, url: str, payload: Any | None = None) -> None:
    if payload is None:
        logger.info("HTTP request started: method=%s url=%s", method, url)
        return
    logger.info("HTTP request started: method=%s url=%s payload=%s", method, url, payload)


def _log_http_success(method: str, url: str, status_code: int, elapsed_seconds: float, response_preview: str = "") -> None:
    if response_preview:
        logger.info(
            "HTTP request succeeded: method=%s url=%s status=%s elapsed=%.3fs response=%s",
            method,
            url,
            status_code,
            elapsed_seconds,
            _truncate(response_preview),
        )
        return
    logger.info(
        "HTTP request succeeded: method=%s url=%s status=%s elapsed=%.3fs",
        method,
        url,
        status_code,
        elapsed_seconds,
    )


def _log_http_failure(method: str, url: str, elapsed_seconds: float, error: Exception) -> None:
    logger.error(
        "HTTP request failed: method=%s url=%s elapsed=%.3fs error=%s",
        method,
        url,
        elapsed_seconds,
        error,
    )


native_tools = [
    {
        "type": "function",
        "name": "connections_target",
        "description": "Get the description of target connections.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "connections_rotate",
        "description": "Rotate a single cell. The cell must be provided in RxC format, where R is row and C is column.",
        "parameters": {
            "type": "object",
            "properties": {
                "cell": {
                    "type": "string",
                    "description": "Cell to rotate in RxC format, e.g. 2x3.",
                }
            },
            "required": ["cell"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "connections_result",
        "description": "Get description of current connections.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "connections_reset",
        "description": "Reset all rotations and start from the beginning.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


NATIVE_TOOL_NAMES = {
    "connections_target",
    "connections_rotate",
    "connections_result",
    "connections_reset",
}


def is_native_tool(name: str) -> bool:
    return name in NATIVE_TOOL_NAMES


async def execute_native_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "connections_target":
        return await connections_target()

    if name == "connections_rotate":
        cell = arguments.get("cell")
        if not isinstance(cell, str) or not cell.strip():
            raise RuntimeError("connections_rotate requires 'cell' in RxC format")
        return await connections_rotate(cell=cell.strip())

    if name == "connections_result":
        return await connections_result()

    if name == "connections_reset":
        return await connections_reset()

    raise RuntimeError(f"Unknown native tool: {name}")


def _error(title: str, status: int, message: str, hint: str = "") -> dict[str, Any]:
    return {
        "error": title,
        "status": status,
        "message": message,
        "hint": hint,
    }


def fetch_image(url: str, save_path: Path) -> dict[str, Any] | None:
    target_path = (PROJECT_ROOT / save_path).resolve()
    try:
        target_path.relative_to(PROJECT_ROOT)
    except ValueError:
        return _error(
            title="Invalid save path",
            status=400,
            message=f"save_path must be relative to PROJECT_ROOT: {save_path}",
            hint="Use a relative path like data/solved_electricity.png.",
        )

    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        _log_http_start("GET", url)
        started_at = time.monotonic()
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        _log_http_success(
            method="GET",
            url=url,
            status_code=response.status_code,
            elapsed_seconds=time.monotonic() - started_at,
        )
        target_path.write_bytes(response.content)
        return None
    except requests.RequestException as error:
        _log_http_failure("GET", url, time.monotonic() - started_at, error)
        status_code = getattr(getattr(error, "response", None), "status_code", 502)
        return _error(
            title="Image download failed",
            status=int(status_code) if isinstance(status_code, int) else 502,
            message=f"Could not download image from {url}: {error}",
            hint="Check HUB_URL availability and network connectivity.",
        )
    except OSError as error:
        return _error(
            title="File save failed",
            status=500,
            message=f"Could not save image to {target_path}: {error}",
            hint="Verify write permissions for PROJECT_ROOT/data.",
        )


async def describe_image(image_path: str) -> dict[str, Any]:
    redis_client: Redis | None = None
    pubsub = None
    try:
        redis_client = Redis.from_url(DEFAULT_REDIS_URL, decode_responses=True)
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(DONE_CHANNEL)

        await redis_client.publish(REQUEST_CHANNEL, image_path)

        deadline = asyncio.get_running_loop().time() + WAIT_TIMEOUT_SECONDS
        while asyncio.get_running_loop().time() < deadline:
            remaining = max(0.0, deadline - asyncio.get_running_loop().time())
            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=min(1.0, remaining),
            )
            if not message:
                continue
            if message.get("type") != "message":
                continue
            data = message.get("data")
            if isinstance(data, str) and data.strip() == image_path:
                info_relative_path = Path(image_path).with_name(f"{Path(image_path).stem}-info.md")
                info_full_path = (PROJECT_ROOT / info_relative_path).resolve()
                try:
                    info_full_path.relative_to(PROJECT_ROOT)
                except ValueError:
                    return _error(
                        title="Invalid info path",
                        status=400,
                        message=f"Resolved info path is outside PROJECT_ROOT: {info_full_path}",
                        hint="Use image paths inside PROJECT_ROOT.",
                    )

                if not info_full_path.is_file():
                    return _error(
                        title="Info file missing",
                        status=404,
                        message=f"Info file not found: {info_relative_path.as_posix()}",
                        hint="Ensure vision worker created the sidecar file after processing.",
                    )

                try:
                    info_content = info_full_path.read_text(encoding="utf-8")
                except OSError as error:
                    return _error(
                        title="Info read failed",
                        status=500,
                        message=f"Could not read info file {info_relative_path.as_posix()}: {error}",
                        hint="Check file permissions and disk state.",
                    )

                return {
                    "status": 200,
                    "content": info_content,
                }

        return _error(
            title="Vision processing timeout",
            status=408,
            message=(
                "No matching message received on vision:done within "
                f"{WAIT_TIMEOUT_SECONDS} seconds."
            ),
            hint="Ensure vision worker is running and subscribed to vision:request.",
        )
    except Exception as error:
        return _error(
            title="Redis communication failed",
            status=503,
            message=f"Could not publish/wait on Redis channels: {error}",
            hint="Check REDIS_URL and verify Redis server is reachable.",
        )
    finally:
        if pubsub is not None:
            await pubsub.close()
        if redis_client is not None:
            await redis_client.aclose()


async def connections_target() -> dict[str, Any]:
    image_url = f"{HUB_URL}/i/solved_electricity.png"
    image_relative_path = Path("data") / "solved_electricity.png"

    image_error = fetch_image(image_url, image_relative_path)
    if image_error is not None:
        return image_error

    return await describe_image(image_relative_path.as_posix())


async def connections_rotate(cell: str) -> dict[str, Any]:
    rotate_url = f"{HUB_URL}/verify"
    query = {
        "apikey": HUB_API_KEY,
        "task": "electricity",
        "answer": {
            "rotate": cell
        }
    }

    try:
        _log_http_start("POST", rotate_url, payload=query)
        started_at = time.monotonic()
        response = requests.post(rotate_url, json=query, timeout=30)
        response.raise_for_status()
        _log_http_success(
            method="POST",
            url=rotate_url,
            status_code=response.status_code,
            elapsed_seconds=time.monotonic() - started_at,
            response_preview=response.text,
        )
        return {
            "status": 200,
            "message": "Rotate successful",
        }
    except requests.RequestException as error:
        _log_http_failure("POST", rotate_url, time.monotonic() - started_at, error)
        status_code = getattr(getattr(error, "response", None), "status_code", 502)
        return _error(
            title="Rotate request failed",
            status=int(status_code) if isinstance(status_code, int) else 502,
            message=f"Could not rotate cell via {rotate_url}: {error}",
            hint="Verify HUB_URL/HUB_API_KEY and request payload.",
        )



async def connections_result() -> dict[str, Any]:
    image_url = f"{HUB_URL}/data/{HUB_API_KEY}/electricity.png"
    image_relative_path = Path("data") / "electricity.png"

    image_error = fetch_image(image_url, image_relative_path)
    if image_error is not None:
        return image_error

    return await describe_image(image_relative_path.as_posix())


async def connections_reset() -> dict[str, Any]:
    reset_url = f"{HUB_URL}/data/{HUB_API_KEY}/electricity.png?reset=1"

    try:
        _log_http_start("GET", reset_url)
        started_at = time.monotonic()
        response = requests.get(reset_url, timeout=30)
        response.raise_for_status()
        _log_http_success(
            method="GET",
            url=reset_url,
            status_code=response.status_code,
            elapsed_seconds=time.monotonic() - started_at,
        )
        return {
            "status": 200,
            "message": "Reset successful",
        }
    except requests.RequestException as error:
        _log_http_failure("GET", reset_url, time.monotonic() - started_at, error)
        status_code = getattr(getattr(error, "response", None), "status_code", 502)
        return _error(
            title="Reset request failed",
            status=int(status_code) if isinstance(status_code, int) else 502,
            message=f"Could not reset state via {reset_url}: {error}",
            hint="Verify HUB_URL/HUB_API_KEY and network connectivity.",
        )

