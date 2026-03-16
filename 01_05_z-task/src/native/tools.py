from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import requests

from ..config import (
    AUTO_API_503_SLEEP_SECONDS,
    AUTO_API_KEY,
    AUTO_API_TASK,
    AUTO_API_URL,
    REQUEST_TIMEOUT_SECONDS,
)
from ..logger import log

native_tools = [
    {
        "type": "function",
        "name": "sleep",
        "description": "Pause execution for a number of seconds (float). Maximum is 60 seconds.",
        "parameters": {
            "type": "object",
            "properties": {
                "seconds": {
                    "type": "number",
                    "description": "Number of seconds to sleep. Must be between 0 and 60.",
                }
            },
            "required": ["seconds"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "auto_api",
        "description": (
            "Call the configured task API endpoint. Provide parameters as an object, e.g. "
            "{\"action\":\"help\"} or {\"action\":\"setstatus\",\"route\":\"a-1\",\"value\":\"RTOPEN\"}. "
            "Returns API response or wait instruction with exact sleep seconds."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action name to execute"
                }
            },
            "required": ["action"],
            "additionalProperties": True,
        },
        "strict": False,
    },
]


class _AutoApiClient:
    def __init__(self) -> None:
        self._next_allowed_epoch = 0.0

    async def call(self, params: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(params, dict):
            raise RuntimeError("params must be an object")

        pre_wait_seconds = self._seconds_until_allowed()
        if pre_wait_seconds > 0:
            return _format_wait_instruction(
                status_code=429,
                error="API rate limit exceeded",
                message="A previous response indicated that you need to wait before the next call.",
                wait_seconds=pre_wait_seconds,
            )

        payload = {
            "apikey": AUTO_API_KEY,
            "task": AUTO_API_TASK,
            "answer": params,
        }

        log.http_request("POST", AUTO_API_URL, payload)

        try:
            response = requests.post(
                AUTO_API_URL,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as error:
            raise RuntimeError(f"auto_api request failed: {error}") from error

        self._update_limit_from_headers(response.headers)

        body = _parse_body(response)
        headers_snapshot = dict(response.headers)
        log.http_response(
            response.status_code,
            {
                "retry-after": headers_snapshot.get("Retry-After", ""),
                "x-ratelimit-reset": headers_snapshot.get("X-RateLimit-Reset", ""),
                "x-ratelimit-reset-after": headers_snapshot.get("X-RateLimit-Reset-After", ""),
                "ratelimit-reset": headers_snapshot.get("RateLimit-Reset", ""),
            },
            _preview(body),
        )

        if response.status_code == 429:
            wait_seconds = max(
                _extract_retry_after_from_body(body),
                _extract_reset_seconds(response.headers) or 0.0,
                self._seconds_until_allowed(),
            )
            if wait_seconds > 0:
                self._next_allowed_epoch = max(self._next_allowed_epoch, time.time() + wait_seconds)
            return _format_wait_instruction(
                status_code=429,
                error="API rate limit exceeded",
                message=_extract_message(body, "API rate limit exceeded. Please retry later."),
                wait_seconds=wait_seconds,
            )

        if response.status_code == 503:
            wait_seconds = max(
                _extract_retry_after_from_body(body),
                _extract_reset_seconds(response.headers) or 0.0,
                AUTO_API_503_SLEEP_SECONDS,
            )
            return _format_wait_instruction(
                status_code=503,
                error="Service Temporarily Unavailable",
                message="The server is currently overloaded and cannot process the request.",
                wait_seconds=wait_seconds,
            )

        return _format_response(response.status_code, body)

    def _seconds_until_allowed(self) -> float:
        return max(0.0, self._next_allowed_epoch - time.time())

    def _update_limit_from_headers(self, headers: requests.structures.CaseInsensitiveDict[str]) -> None:
        reset_seconds = _extract_reset_seconds(headers)
        if reset_seconds is None:
            return
        candidate = time.time() + max(0.0, reset_seconds)
        self._next_allowed_epoch = max(self._next_allowed_epoch, candidate)


def _parse_body(response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text


def _format_response(status_code: int, body: Any) -> dict[str, Any]:
    if status_code >= 400:
        return _format_error_response(status_code, body)
    return {
        "status_code": status_code,
        "response": body,
    }


def _format_error_response(status_code: int, body: Any) -> dict[str, Any]:
    error_text = "Request failed"
    message_text = "API request failed."

    if isinstance(body, dict):
        error_text = str(
            body.get("error")
            or body.get("title")
            or body.get("statusText")
            or error_text
        )
        message_text = str(
            body.get("message")
            or body.get("detail")
            or body.get("description")
            or message_text
        )
    elif isinstance(body, str) and body.strip():
        message_text = body.strip()

    if status_code == 503:
        return _format_wait_instruction(
            status_code=503,
            error="Service Temporarily Unavailable",
            message="The server is currently overloaded and cannot process the request.",
            wait_seconds=AUTO_API_503_SLEEP_SECONDS,
        )

    hint_text = "Check action name and required fields in params object, then retry."
    if status_code == 429:
        retry_after = _extract_retry_after_from_body(body)
        if retry_after > 0:
            hint_text = (
                f"Rate limit exceeded. Wait exactly {int(round(retry_after))} seconds, "
                "then call sleep with that value and retry the exact same action."
            )
        else:
            hint_text = "Rate limit exceeded. Wait for reset time, call sleep, then retry the exact same action."

        if isinstance(body, dict):
            error_text = str(body.get("error") or body.get("message") or "API rate limit exceeded")

    return {
        "error": error_text,
        "status": status_code,
        "message": message_text,
        "hint": hint_text,
    }


def _extract_retry_after_from_body(body: Any) -> float:
    if not isinstance(body, dict):
        return 0.0

    raw = body.get("retry_after")
    if raw is None:
        return 0.0

    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return 0.0


def _extract_message(body: Any, fallback: str) -> str:
    if isinstance(body, dict):
        candidate = body.get("message") or body.get("detail") or body.get("description")
        if candidate:
            return str(candidate)
    elif isinstance(body, str) and body.strip():
        return body.strip()
    return fallback


def _format_wait_instruction(
    *,
    status_code: int,
    error: str,
    message: str,
    wait_seconds: float,
) -> dict[str, Any]:
    seconds_int = max(1, int(round(wait_seconds)))
    return {
        "error": error,
        "status": status_code,
        "message": message,
        "hint": (
            f"Wait exactly {seconds_int} seconds, then call sleep with {seconds_int} "
            "and retry the exact same action."
        ),
        "wait_seconds": seconds_int,
    }


def _preview(body: Any) -> str:
    if isinstance(body, str):
        return body
    try:
        return json.dumps(body, ensure_ascii=False)
    except Exception:
        return str(body)


def _extract_reset_seconds(headers: requests.structures.CaseInsensitiveDict[str]) -> float | None:
    candidates = [
        headers.get("Retry-After"),
        headers.get("X-RateLimit-Reset-After"),
        headers.get("RateLimit-Reset"),
        headers.get("X-RateLimit-Reset"),
        headers.get("X-Rate-Limit-Reset"),
    ]

    now = datetime.now(timezone.utc)
    for raw in candidates:
        if not raw:
            continue
        value = raw.strip()

        try:
            numeric = float(value)
            if numeric > 1_000_000_000:
                return max(0.0, numeric - time.time())
            return max(0.0, numeric)
        except ValueError:
            pass

        try:
            parsed = parsedate_to_datetime(value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            delta = (parsed - now).total_seconds()
            return max(0.0, delta)
        except Exception:
            continue

    return None


_auto_api_client = _AutoApiClient()


async def execute_native_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "sleep":
        return await sleep(**arguments)
    if name == "auto_api":
        return await auto_api(arguments)
    raise RuntimeError(f"Unknown native tool: {name}")


async def sleep(seconds: float) -> dict[str, str]:
    value = float(seconds)
    if value < 0:
        raise RuntimeError("seconds must be >= 0")
    if value > 60:
        raise RuntimeError("seconds must be <= 60")

    log.info(f"Sleep for {value}")
    await asyncio.sleep(value)
    status = f"Sleep done, slept for {value} seconds"
    log.info(status)
    return {"status": status}


async def auto_api(params: dict[str, Any]) -> dict[str, Any]:
    return await _auto_api_client.call(params)
