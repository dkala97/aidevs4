from __future__ import annotations

import json
from contextlib import AsyncExitStack
from typing import Any
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .config import AgentConfig
from .logger import log

MCP_NS_SEPARATOR = "__"

def get_default_mcp_config_path(project_root: Path):
    return project_root / "mcp.json"

import os
import re

def substitute_env_vars(value: Any) -> Any:
    """
    Recursively substitute environment variables in config values.

    Replaces patterns like "${VARNAME}" with os.getenv("VARNAME", "").
    Handles strings, lists, dicts, and nested structures.

    Args:
        value: The value to process (can be str, list, dict, or any nested combination)

    Returns:
        The value with environment variables substituted
    """
    if isinstance(value, str):
        # Replace ${VARNAME} patterns with environment variable values
        def replace_var(match):
            var_name = match.group(1)
            return os.getenv(var_name, "")
        return re.sub(r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}', replace_var, value)

    elif isinstance(value, list):
        return [substitute_env_vars(item) for item in value]

    elif isinstance(value, dict):
        return {key: substitute_env_vars(val) for key, val in value.items()}

    else:
        return value
class McpError(RuntimeError):
    # TODO: log errors
    pass

def mcp_client_route(mcp_clients: dict[str, McpClient], server_or_tool_name: str) -> McpClient:
    server_name = server_or_tool_name if MCP_NS_SEPARATOR not in server_or_tool_name else server_or_tool_name.split(MCP_NS_SEPARATOR)[0]
    if server_name in mcp_clients:
        return mcp_clients[server_name]
    raise McpError(f"Missing MCP server: {server_name}")

class McpClient:
    def __init__(self, agent_config: AgentConfig, server_name: str, config_path: str | None = None) -> None:
        self._exit_stack = AsyncExitStack()
        self._session: ClientSession | None = None
        self._agent_config = agent_config
        self._server_name: str = server_name
        self._config_path: str = config_path if config_path else get_default_mcp_config_path(agent_config.PROJECT_ROOT)

    @staticmethod
    def create_clients_from_config(agent_config: AgentConfig, mcp_config_path: str | None = None, servers: list[str] = None) -> dict[str, McpClient] :
        mcp_clients = {}
        mcp_config = mcp_config_path if mcp_config_path else get_default_mcp_config_path(agent_config.PROJECT_ROOT)
        config = McpClient._load_mcp_config(mcp_config)
        servers_to_create = [ name for name, _ in config.get("mcpServers", {}).items() if not servers or name in servers ]
        for server_name in servers_to_create:
            mcp_clients[server_name] = McpClient(agent_config, server_name, mcp_config)
        return mcp_clients

    @property
    def session(self) -> ClientSession:
        if self._session is None:
            raise McpError("MCP client is not connected")
        return self._session

    async def connect(self) -> None:
        config = self._load_mcp_config(self._config_path)
        server_config = config.get("mcpServers", {}).get(self._server_name)
        if not server_config:
            raise McpError(f'MCP server "{self._server_name}" not found in mcp.json')

        command = server_config.get("command")
        if not command:
            raise McpError(f'MCP server "{self._server_name}" is missing the command field')
        cwd = str(server_config.get("cwd", self._agent_config.PROJECT_ROOT))
        cwd = cwd.replace("${PROJECT_ROOT}", self._agent_config.PROJECT_ROOT.as_posix())

        args = [str(arg) for arg in server_config.get("args", [])]
        env = {key: str(value) for key, value in server_config.get("env", {}).items()}

        # Substitute environment variables in config values
        command = str(substitute_env_vars(command))
        cwd = str(substitute_env_vars(cwd))
        args = [str(arg) for arg in substitute_env_vars(args)]
        env = {key: str(value) for key, value in substitute_env_vars(env).items()}

        # Also handle PROJECT_ROOT substitution after env var replacement
        cwd = cwd.replace("${PROJECT_ROOT}", self._agent_config.PROJECT_ROOT.as_posix())

        log.info(f"Spawning MCP server: {self._server_name}")
        log.info(f"Command: {command} {' '.join(args)}")

        transport = await self._exit_stack.enter_async_context(
            stdio_client(
                StdioServerParameters(
                    command=str(command),
                    args=args,
                    env=env,
                    cwd=cwd,
                )
            )
        )
        read_stream, write_stream = transport

        session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )

        try:
            await session.initialize()
        except Exception as error:
            await self._exit_stack.aclose()
            raise McpError(f"Failed to initialize MCP session: {error}") from error

        self._session = session
        log.success(f"Connected to {self._server_name} via stdio")

    async def close(self) -> None:
        await self._exit_stack.aclose()
        self._session = None

    async def list_tools(self) -> list[dict[str, Any]]:
        result = await self.session.list_tools()
        tools = []
        for tool in result.tools:
            item = self._model_to_dict(tool)
            tools.append(
                {
                    "name": f"{self._server_name}{MCP_NS_SEPARATOR}{item.get("name", "")}",
                    "description": item.get("description", ""),
                    "inputSchema": item.get("inputSchema") or item.get("input_schema") or {"type": "object"},
                }
            )
        return tools

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        name_without_namespace=name.removeprefix(f"{self._server_name}{MCP_NS_SEPARATOR}")
        try:
            result = await self.session.call_tool(name_without_namespace, arguments=arguments)
        except Exception as error:
            raise McpError(f"MCP tool '{name}' failed: {error}") from error

        is_error = bool(getattr(result, "isError", False) or getattr(result, "is_error", False))
        structured = getattr(result, "structuredContent", None)
        if structured is None:
            structured = getattr(result, "structured_content", None)

        if structured is not None:
            if is_error:
                raise McpError(json.dumps(structured, ensure_ascii=True))
            return structured

        parsed_blocks = [self._parse_content_block(content) for content in getattr(result, "content", [])]
        parsed_blocks = [block for block in parsed_blocks if block is not None]

        if is_error:
            raise McpError(self._collapse_blocks(parsed_blocks))

        if not parsed_blocks:
            return {}
        if len(parsed_blocks) == 1:
            return parsed_blocks[0]
        return parsed_blocks

    @staticmethod
    def mcp_tools_to_openai(mcp_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("inputSchema", {"type": "object"}),
                "strict": False,
            }
            for tool in mcp_tools
        ]

    @staticmethod
    def _load_mcp_config(config_path: str) -> dict[str, Any]:
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except FileNotFoundError as error:
            log.warn(f"Missing MCP config: {config_path}")
            return {}
        except json.JSONDecodeError as error:
            raise McpError(f"Invalid JSON in {config_path}: {error}") from error

    @staticmethod
    def _model_to_dict(value: Any) -> dict[str, Any]:
        if hasattr(value, "model_dump"):
            return value.model_dump(by_alias=True, exclude_none=True)
        if isinstance(value, dict):
            return value
        raise McpError(f"Unsupported MCP object type: {type(value)!r}")

    def _parse_content_block(self, content: Any) -> Any:
        block_type = getattr(content, "type", None)
        if block_type == "text":
            text = getattr(content, "text", "")
            if not text:
                return None
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text

        if block_type == "image":
            return {
                "type": "image",
                "mimeType": getattr(content, "mimeType", None),
                "data": getattr(content, "data", None),
            }

        if block_type == "resource":
            resource = getattr(content, "resource", None)
            if resource is None:
                return None
            resource_dict = self._model_to_dict(resource)
            text = resource_dict.get("text")
            if isinstance(text, str):
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return text
            return resource_dict

        if hasattr(content, "model_dump"):
            return content.model_dump(by_alias=True, exclude_none=True)

        return str(content)

    @staticmethod
    def _collapse_blocks(blocks: list[Any]) -> str:
        if not blocks:
            return "Unknown MCP tool error"

        if len(blocks) == 1:
            block = blocks[0]
            return block if isinstance(block, str) else json.dumps(block, ensure_ascii=True)

        return json.dumps(blocks, ensure_ascii=True)