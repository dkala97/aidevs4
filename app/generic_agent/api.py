from __future__ import annotations

from typing import Any

import requests
from .config import AgentConfig


def chat(
    *,
    config: AgentConfig,
    input_items: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str = "auto",
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": config.MODEL,
        "input": input_items,
    }

    if tools:
        body["tools"] = tools
        body["tool_choice"] = tool_choice

    if config.INSTRUCTIONS:
        body["instructions"] = config.INSTRUCTIONS

    if config.MAX_OUTPUT_TOKENS:
        body["max_output_tokens"] = config.MAX_OUTPUT_TOKENS

    response = requests.post(
        config.RESPONSES_API_ENDPOINT,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.AI_API_KEY}",
            **config.EXTRA_API_HEADERS,
        },
        json=body,
        timeout=config.REQUEST_TIMEOUT_SECONDS,
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