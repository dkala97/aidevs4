from __future__ import annotations

from typing import Any

import requests

from ..config import (
    AI_API_KEY,
    EXTRA_API_HEADERS,
    REQUEST_TIMEOUT_SECONDS,
    RESPONSES_API_ENDPOINT,
    VISION_MODEL,
)


def analyze_image(*, image_base64: str, mime_type: str, question: str) -> str:
    response = requests.post(
        RESPONSES_API_ENDPOINT,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AI_API_KEY}",
            **EXTRA_API_HEADERS,
        },
        json={
            "model": VISION_MODEL,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": question},
                        {
                            "type": "input_image",
                            "image_url": f"data:{mime_type};base64,{image_base64}",
                        },
                    ],
                }
            ],
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    data: dict[str, Any] = response.json()
    if not response.ok or data.get("error"):
        message = data.get("error", {}).get("message") or f"Vision request failed ({response.status_code})"
        raise RuntimeError(message)

    output_text = data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    for item in data.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text", "").strip():
                return content["text"].strip()

    return "No response"