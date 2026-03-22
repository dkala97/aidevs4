#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Any
from pathlib import Path

from .agent import run
from .logger import log
from .mcp_client import McpClient, McpError
from .native_tools_if import NativeToolsFactoryIf, NativeToolsFactoryStub
from .config import AgentConfig

global_app_description=""

def app_setup_arg_parser(app_description: str = "Generic AI agent app") -> argparse.ArgumentParser:
    global global_app_description
    global_app_description=app_description
    parser = argparse.ArgumentParser(description=app_description)
    query_group = parser.add_mutually_exclusive_group(required=True)
    query_group.add_argument(
        "--query",
        help="User query sent to the agent.",
    )
    query_group.add_argument(
        "--query_file",
        help="User query file sent to the agent.",
    )
    parser.add_argument(
        "--server",
        default=None,
        type=list[str],
        action="append",
        help="List of server names from mcp config to use. Defaults to all available servers.",
    )
    parser.add_argument(
        "--mcp_config",
        default=None,
        type=str,
        help="Path to mcp config file",
    )
    return parser


async def app_async_main(config: AgentConfig, args: argparse.Namespace, native_tools_factory: NativeToolsFactoryIf = NativeToolsFactoryStub()) -> int:
    mcp_client: McpClient | None = None

    try:
        log.box(global_app_description)

        query = args.query
        if not query:
            with open(args.query_file) as query_file:
                query = query_file.read()

        mcp_tools_list: list[dict[str, Any]] = []
        native_tools_list: list[dict[str, Any]] = []

        mcp_clients = McpClient.create_clients_from_config(config, args.mcp_config, args.server)
        for server_name, mcp_client in mcp_clients.items():
            log.start(f"Connecting to MCP server '{server_name}'...")
            await mcp_client.connect()
            mcp_tools = await mcp_client.list_tools()
            mcp_tools_list.extend(mcp_tools)
            log.success(
                "MCP: " + ", ".join(tool["name"] for tool in mcp_tools) if mcp_tools else "MCP: no tools"
            )

        native_tools = native_tools_factory.create_native_tools(args)
        native_tools_list = native_tools.list_tools()
        if len(native_tools_list) > 0:
            log.success(
                "Native: " + ", ".join(tool["name"] for tool in native_tools_list)
            )
        else:
            log.info("No native tools provided")

        log.start("Starting agent loop...")
        result = await run(config, query, mcp_clients=mcp_clients, mcp_tools=mcp_tools_list, native_tools=native_tools, native_tools_list=native_tools_list)

        log.success("Agent finished")
        print()
        print(result["response"])
        return 0
    except (McpError, RuntimeError, ValueError) as error:
        log.error("Startup error", str(error))
        return 1
    finally:
        if mcp_client is not None:
            await mcp_client.close()


def app_main(config: AgentConfig, args: argparse.Namespace, native_tools_factory: NativeToolsFactoryIf = NativeToolsFactoryStub()) -> int:
    try:
        return asyncio.run(app_async_main(config, args, native_tools_factory))
    except KeyboardInterrupt:
        log.warn("Interrupted")
        return 130


if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).resolve().parent
    REPO_ROOT = PROJECT_ROOT.parent.parent
    ENV_PATH = REPO_ROOT / ".env"
    config = AgentConfig(ENV_PATH, PROJECT_ROOT, "Say hi")
    sys.exit(app_main(config, app_setup_arg_parser().parse_args()))
