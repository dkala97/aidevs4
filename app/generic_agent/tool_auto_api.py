from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import requests

from .logger import log


class ToolAutoApiConfig:
    def __init__(self, endpoint: str, payload_prototype: dict[str, Any]):
        self.ENDPOINT_URL=endpoint
        self.PAYLOAD_PROTOTYPE=payload_prototype
        self.ERROR_503_SLEEP_SECONDS=10
        self.REQUEST_TIMEOUT_SECONDS=10


def create_tool_schema_auto_api(tool_name: str, description: str, parameters: Any):
    # Example:
    _ = {
        "type": "function",
        "name": "auto_api",
        "description": (
            "Call the configured task API endpoint. Provide parameters as an object, e.g. "
            "{\"action\":\"help\"} or {\"action\":\"someaction\",\"actionarg1\":\"example\"}. "
            "Returns API response."
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
    }

    return {
        "type": "function",
        "name": tool_name,
        "description": description,
        "parameters": parameters,
        "strict": False,
    }

class ToolAutoApi:
    def __init__(self, config: AutoApiConfig) -> None:
        self._next_allowed_epoch = 0.0
        self._config = config

    async def call(self, params: dict[str, Any]) ->Any:
        if not isinstance(params, dict):
            raise RuntimeError("params must be an object")

        pre_wait_seconds = self._seconds_until_allowed()
        if pre_wait_seconds > 0:
            return self._format_wait_instruction(
                status_code=429,
                error="API rate limit exceeded",
                message="A previous response indicated that you need to wait before the next call.",
                wait_seconds=pre_wait_seconds,
            )

        payload = self._config.PAYLOAD_PROTOTYPE
        for key, value in params.items():
            payload[key] = value

        log.http_request("POST", self._config.ENDPOINT_URL, payload)

        try:
            response = requests.post(
                self._config.ENDPOINT_URL,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=self._config.REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as error:
            raise RuntimeError(f"auto_api request failed: {error}") from error

        self._update_limit_from_headers(response.headers)

        body = self._parse_body(response)
        headers_snapshot = dict(response.headers)
        log.http_response(
            response.status_code,
            {
                "retry-after": headers_snapshot.get("Retry-After", ""),
                "x-ratelimit-reset": headers_snapshot.get("X-RateLimit-Reset", ""),
                "x-ratelimit-reset-after": headers_snapshot.get("X-RateLimit-Reset-After", ""),
                "ratelimit-reset": headers_snapshot.get("RateLimit-Reset", ""),
            },
            self._preview(body),
        )

        if response.status_code == 429:
            wait_seconds = max(
                self._extract_retry_after_from_body(body),
                self._extract_reset_seconds(response.headers) or 0.0,
                self._seconds_until_allowed(),
            )
            if wait_seconds > 0:
                self._next_allowed_epoch = max(self._next_allowed_epoch, time.time() + wait_seconds)
            return self._format_wait_instruction(
                status_code=429,
                error="API rate limit exceeded",
                message=self._extract_message(body, "API rate limit exceeded. Please retry later."),
                wait_seconds=wait_seconds,
            )

        if response.status_code == 503:
            wait_seconds = max(
                self._extract_retry_after_from_body(body),
                self._extract_reset_seconds(response.headers) or 0.0,
                self._config.ERROR_503_SLEEP_SECONDS,
            )
            return self._format_wait_instruction(
                status_code=503,
                error="Service Temporarily Unavailable",
                message="The server is currently overloaded and cannot process the request.",
                wait_seconds=wait_seconds,
            )

        return self._format_response(response.status_code, body)

    def _seconds_until_allowed(self) -> float:
        return max(0.0, self._next_allowed_epoch - time.time())

    def _update_limit_from_headers(self, headers: requests.structures.CaseInsensitiveDict[str]) -> None:
        reset_seconds = self._extract_reset_seconds(headers)
        if reset_seconds is None:
            return
        candidate = time.time() + max(0.0, reset_seconds)
        self._next_allowed_epoch = max(self._next_allowed_epoch, candidate)


    def _parse_body(self, response: requests.Response) -> Any:
        try:
            return response.json()
        except ValueError:
            return response.text


    def _format_response(self, status_code: int, body: Any) -> dict[str, Any]:
        if status_code >= 400:
            return self._format_error_response(status_code, body)
        return {
            "status_code": status_code,
            "response": body,
        }


    def _format_error_response(self, status_code: int, body: Any) -> dict[str, Any]:
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
            return self._format_wait_instruction(
                status_code=503,
                error="Service Temporarily Unavailable",
                message="The server is currently overloaded and cannot process the request.",
                wait_seconds=self._config.ERROR_503_SLEEP_SECONDS,
            )

        hint_text = "Check action name and required fields in params object, then retry."
        if status_code == 429:
            retry_after = self._extract_retry_after_from_body(body)
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


    def _extract_retry_after_from_body(self, body: Any) -> float:
        if not isinstance(body, dict):
            return 0.0

        raw = body.get("retry_after")
        if raw is None:
            return 0.0

        try:
            return max(0.0, float(raw))
        except (TypeError, ValueError):
            return 0.0


    def _extract_message(self, body: Any, fallback: str) -> str:
        if isinstance(body, dict):
            candidate = body.get("message") or body.get("detail") or body.get("description")
            if candidate:
                return str(candidate)
        elif isinstance(body, str) and body.strip():
            return body.strip()
        return fallback


    def _format_wait_instruction(self,
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


    def _preview(self, body: Any) -> str:
        if isinstance(body, str):
            return body
        try:
            return json.dumps(body, ensure_ascii=False)
        except Exception:
            return str(body)


    def _extract_reset_seconds(self, headers: requests.structures.CaseInsensitiveDict[str]) -> float | None:
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
