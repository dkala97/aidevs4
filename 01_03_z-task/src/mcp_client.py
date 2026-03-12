from __future__ import annotations

import json
import time
from typing import Any

import requests

from .config import PARCELS_MCP_HOST, PARCELS_MCP_PORT, PARCELS_MCP_URL
from .logging_utils import log


class McpError(RuntimeError):
    pass

class ParcelsMcpClient:
    def __init__(self) -> None:
        self.base_url = PARCELS_MCP_URL or f"http://{PARCELS_MCP_HOST}:{PARCELS_MCP_PORT}/mcp"
        self.health_url = self.base_url.rsplit("/mcp", 1)[0] + "/health"
        self.session = requests.Session()
        self.session_id: str | None = None
        self._rpc_id = 1

    def start(self) -> None:
        log(f"Connecting to parcels MCP: {self.base_url}")
        self._wait_until_ready(timeout_seconds=20)
        self._initialize_session()
        tools = self.list_tools()
        tool_names = ", ".join(tool.get("name", "?") for tool in tools)
        log(f"MCP ready. Tools: {tool_names}")

    def close(self) -> None:
        pass

    def _wait_until_ready(self, timeout_seconds: int) -> None:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            try:
                response = self.session.get(self.health_url, timeout=2)
                if response.ok:
                    return
            except requests.RequestException:
                pass

            time.sleep(0.4)

        raise McpError(f"MCP server not ready at {self.health_url}")

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        return headers

    def _rpc(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        is_notification: bool = False,
        include_headers: bool = False,
    ) -> dict[str, Any] | tuple[dict[str, Any], requests.structures.CaseInsensitiveDict[str]] | None:
        payload: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        if not is_notification:
            payload["id"] = self._rpc_id
            self._rpc_id += 1

        if is_notification:
            response = self.session.post(
                self.base_url,
                headers=self._headers(),
                json=payload,
                timeout=10,
                stream=True,
            )
            if response.status_code >= 400:
                response_text = response.text
                response.close()
                raise McpError(f"MCP notification failed ({response.status_code}): {response_text}")
            response.close()
            return None

        response = self.session.post(
            self.base_url,
            headers=self._headers(),
            json=payload,
            timeout=30,
            stream=True,
        )

        content_type = (response.headers.get("Content-Type") or "").lower()

        if "text/event-stream" in content_type:
            parsed_data: dict[str, Any] | None = None

            json_payload = response.text[response.text.find("data:")+5:].strip()
            try:
                parsed_data = json.loads(json_payload)
            except json.JSONDecodeError:
                pass

            response.close()
            if parsed_data is None:
                raise McpError("Invalid MCP JSON response: missing data payload in SSE stream")
            data = parsed_data
        else:
            try:
                data = response.json()
            except json.JSONDecodeError as error:
                text = response.text or ""
                response.close()
                raise McpError(f"Invalid MCP JSON response: {text[:200]}") from error
            response.close()

        if response.status_code >= 400:
            raise McpError(f"MCP request failed ({response.status_code}): {data}")

        if "error" in data and data["error"]:
            message = data["error"].get("message", "Unknown MCP error")
            raise McpError(message)

        if include_headers:
            return data, response.headers

        return data

    def _initialize_session(self) -> None:
        rpc_result = self._rpc(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "clientInfo": {"name": "proxy-assistant-python", "version": "1.0.0"},
                "capabilities": {},
            },
            include_headers=True,
        )

        if not rpc_result:
            raise McpError("Empty initialize response")

        data, headers = rpc_result
        session_id = headers.get("Mcp-Session-Id")
        if not session_id:
            session_id = data.get("result", {}).get("sessionId")

        self.session_id = session_id

        if not self.session_id:
            raise McpError("Brak Mcp-Session-Id po initialize")

        self._rpc("notifications/initialized", {}, is_notification=True)

    def list_tools(self) -> list[dict[str, Any]]:
        data = self._rpc("tools/list")
        if not data:
            return []
        return data.get("result", {}).get("tools", [])

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        data = self._rpc("tools/call", {"name": name, "arguments": arguments})
        if not data:
            raise McpError("Empty tools/call response")
        return data.get("result", {})
