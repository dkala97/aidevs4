from __future__ import annotations

from typing import Any

from .logger import log
from .mcp_client import McpClient
from .config import AgentConfig

def create_tool_schema_fetch_html_body(tool_name: str = "fetch_html_body"):
    return {
        "type": "function",
        "name": tool_name,
        "description": "Fetch page html body based on the page path.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Page path on the server, relative to the website root. Must start with `/`. To access root webpage use `/`.",
                }
            },
            "required": ["path"],
            "additionalProperties": False,
        },
        "strict": True,
    }

class ToolFetchHtmlBody:
    def __init__(self, root_url: str, config: AgentConfig):
        self._root_url = root_url
        self._wrapped_server_name = "playwright"
        mcp_clients = McpClient.create_clients_from_config(config, None, servers=[self._wrapped_server_name])
        if self._wrapped_server_name in mcp_clients:
            self._mcp_client = mcp_clients[self._wrapped_server_name]
        else:
            raise RuntimeError(f"Failed to create server: {self._wrapped_server_name}")
        self._mcp_tools = None

    async def connect_to_mcp(self):
        log.start(f"Connecting to MCP server '{self._wrapped_server_name}'...")
        await self._mcp_client.connect()
        self._mcp_tools = await self._mcp_client.list_tools()
        log.success(
            "ToolFetchHtmlBody - MCP: " + ", ".join(tool["name"] for tool in self._mcp_tools) if self._mcp_tools else "MCP: no tools"
        )

    async def call(self, params: dict[str, Any]) ->Any:
        try:
            return await self._call_throwing(params)
        except Exception as ex:
            return {"status": f"error: {ex}"}

    async def _call_throwing(self, params: dict[str, Any]) -> Any:
        if "path" not in params:
            raise RuntimeError("Missing required parameter: path: string")

        path = str(params["path"]).strip()
        if not path:
            raise RuntimeError("path must be a non-empty string")
        if not path.startswith("/"):
            raise RuntimeError("path must start with '/'")

        if self._mcp_tools is None:
            await self.connect_to_mcp()

        target_url = f"{self._root_url}{path}"
        log.info(f"Fetching HTML body from {target_url}")

        await self._mcp_client.call_tool("playwright__browser_navigate", {"url": target_url})

        page_body = await self._mcp_client.call_tool(
            "playwright__browser_evaluate",
            {"function": "() => document.body ? document.body.outerHTML : ''"},
        )
        if not isinstance(page_body, str):
            raise RuntimeError(f"Unexpected body type from browser_evaluate: {type(page_body)}")

        return {"PageBody": page_body}
