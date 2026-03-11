from __future__ import annotations

from typing import Any


def extract_tool_calls(response: Any) -> list[Any]:
    return [item for item in response.output if item.type == "function_call"]


def extract_text(response: Any) -> str | None:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    for item in response.output:
        if item.type != "message":
            continue

        for content in item.content:
            if content.type == "output_text" and content.text.strip():
                return content.text

    return None
