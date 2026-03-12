from __future__ import annotations

from typing import Any


def mcp_tools_to_openai(mcp_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "name": tool["name"],
            "description": tool.get("description", ""),
            "parameters": tool.get("inputSchema", {"type": "object", "properties": {}}),
            "strict": False,
        }
        for tool in mcp_tools
    ]


def extract_tool_calls(response: Any) -> list[Any]:
    output = getattr(response, "output", []) or []
    return [item for item in output if getattr(item, "type", None) == "function_call"]


def extract_text(response: Any) -> str | None:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    output = getattr(response, "output", []) or []
    for item in output:
        if getattr(item, "type", None) != "message":
            continue
        for content in getattr(item, "content", []) or []:
            content_type = getattr(content, "type", None)
            if content_type in {"output_text", "text"}:
                text = getattr(content, "text", None)
                if isinstance(text, str) and text.strip():
                    return text.strip()

    return None
