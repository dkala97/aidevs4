from __future__ import annotations

from typing import Any

import requests

from .config import (
    AI_API_KEY,
    EXTRA_API_HEADERS,
    INSTRUCTIONS,
    MAX_OUTPUT_TOKENS,
    MODEL,
    REQUEST_TIMEOUT_SECONDS,
    RESPONSES_API_ENDPOINT,
)


def chat(
    *,
    input_items: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    model: str = MODEL,
    instructions: str = INSTRUCTIONS,
    tool_choice: str = "auto",
    max_output_tokens: int = MAX_OUTPUT_TOKENS,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": model,
        "input": input_items,
    }

    if tools:
        body["tools"] = tools
        body["tool_choice"] = tool_choice

    if instructions:
        body["instructions"] = instructions

    if max_output_tokens:
        body["max_output_tokens"] = max_output_tokens

    response = requests.post(
        RESPONSES_API_ENDPOINT,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AI_API_KEY}",
            **EXTRA_API_HEADERS,
        },
        json=body,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    data = response.json()
    if not response.ok or data.get("error"):
        message = data.get("error", {}).get("message") or f"Responses API request failed ({response.status_code})"
        raise RuntimeError(message)

    return data


def extract_tool_calls(response: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in response.get("output", []) if item.get("type") == "function_call"]


def extract_text(response: dict[str, Any]) -> str | None:
    output_text = response.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    for item in response.get("output", []):
        if item.get("type") != "message":
            continue

        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text", "").strip():
                return content["text"].strip()

    return None
