from __future__ import annotations

import json
from typing import Any

from .api import chat, extract_text, extract_tool_calls
from .logger import log
from .mcp_client import McpClient, mcp_client_route
from .native_tools_if import NativeToolsIf
from .config import AgentConfig


async def _run_tool(mcp_clients: dict[str, McpClient], native_tools: NativeToolsIf, tool_call: dict[str, Any]) -> dict[str, Any]:
    name = tool_call["name"]
    raw_arguments = tool_call.get("arguments") or "{}"
    arguments = json.loads(raw_arguments)
    log.tool(name, arguments)

    try:
        result = (
            await native_tools.execute_native_tool(name, arguments)
            if native_tools.is_native_tool(name)
            else await mcp_client_route(mcp_clients, name).call_tool(name, arguments)
        )
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
    config: AgentConfig,
    query: str,
    *,
    mcp_clients: dict[str, McpClient],
    mcp_tools: list[dict[str, Any]],
    native_tools: NativeToolsIf,
    native_tools_list: list[dict[str, Any]],
) -> dict[str, Any]:
    tools = [*McpClient.mcp_tools_to_openai(mcp_tools), *native_tools_list]
    messages: list[dict[str, Any]] = [{"role": "user", "content": query}]
    tool_history: list[dict[str, Any]] = []

    log.query(query)

    for step in range(1, config.MAX_AGENT_STEPS + 1):
        log.api(step, len(messages))
        response = chat(config=config, input_items=messages, tools=tools)
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
            results.append(await _run_tool(mcp_clients, native_tools, tool_call))

        messages.extend(results)

    raise RuntimeError(f"Max steps ({config.MAX_AGENT_STEPS}) reached")
