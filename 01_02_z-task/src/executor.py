from __future__ import annotations

import json
from typing import Any

from .api import extract_text, extract_tool_calls
from .config import MAX_TOOL_ROUNDS, ai


def _log_query(query: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"Query: {query}")
    print("=" * 60)


def _log_result(text: str) -> None:
    print(f"\nA: {text}")


def _execute_tool_calls(tool_calls: list[Any], handlers: dict[str, Any]) -> list[dict[str, str]]:
    print(f"\nTool calls: {len(tool_calls)}")
    outputs: list[dict[str, str]] = []

    for call in tool_calls:
        args = json.loads(call.arguments)
        print(f"  → {call.name}({json.dumps(args, ensure_ascii=False)})")

        try:
            handler = handlers.get(call.name)
            if not handler:
                raise ValueError(f"Unknown tool: {call.name}")

            result = handler(args)
            print("    ✓ Success")
            outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(result, ensure_ascii=False),
                }
            )
        except Exception as error:
            print(f"    ✗ Error: {error}")
            outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps({"error": str(error)}, ensure_ascii=False),
                }
            )

    return outputs


def process_query(query: str, *, model: str, tools: list[dict[str, Any]], handlers: dict[str, Any], instructions: str) -> str:
    _log_query(query)

    conversation = [{"role": "user", "content": query}]

    for _ in range(MAX_TOOL_ROUNDS):
        response = ai.responses.create(
            model=model,
            input=conversation,
            tools=tools,
            tool_choice="auto",
            instructions=instructions,
        )

        tool_calls = extract_tool_calls(response)

        if not tool_calls:
            text = extract_text(response) or "No response"
            _log_result(text)
            return text

        tool_outputs = _execute_tool_calls(tool_calls, handlers)

        conversation.extend(tool_calls)
        conversation.extend(tool_outputs)

    text = "Max tool rounds reached"
    _log_result(text)
    return text
