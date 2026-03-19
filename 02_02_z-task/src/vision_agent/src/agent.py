from __future__ import annotations

import json
from typing import Any

from .api import chat, extract_text, extract_tool_calls
from .logger import log
from .native.tools import execute_native_tool, native_tools

MAX_STEPS = 100


async def _run_tool(tool_call: dict[str, Any]) -> dict[str, Any]:
    name = tool_call["name"]
    raw_arguments = tool_call.get("arguments") or "{}"
    arguments = json.loads(raw_arguments)
    log.tool(name, arguments)

    try:
        result = await execute_native_tool(name, arguments)
        output = json.dumps(result, ensure_ascii=True)
        log.tool_result(name, True, output)
    except Exception as error:
        output = json.dumps({"error": str(error)}, ensure_ascii=True)
        log.tool_result(name, False, str(error))

    return {
        "type": "function_call_output",
        "call_id": tool_call["call_id"],
        "output": output,
    }


async def run(
    query: str,
) -> dict[str, Any]:
    tools = [*native_tools]
    messages: list[dict[str, Any]] = [{"role": "user", "content": query}]
    tool_history: list[dict[str, Any]] = []

    log.query(query)

    for step in range(1, MAX_STEPS + 1):
        log.api(step, len(messages))
        response = chat(input_items=messages, tools=tools)
        log.api_done(response.get("usage"))

        tool_calls = extract_tool_calls(response)
        if not tool_calls:
            text = extract_text(response) or "No response"
            return {"response": text, "tool_calls": tool_history}

        messages.extend(response.get("output", []))

        for tool_call in tool_calls:
            tool_history.append(
                {
                    "name": tool_call["name"],
                    "arguments": json.loads(tool_call.get("arguments") or "{}"),
                }
            )

        results = []
        for tool_call in tool_calls:
            results.append(await _run_tool(tool_call))

        messages.extend(results)

    raise RuntimeError(f"Max steps ({MAX_STEPS}) reached")