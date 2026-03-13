#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import sys

from src.agent import run
from src.config import DEFAULT_QUERY, DEFAULT_SERVER_NAME
from src.logger import log
from src.mcp_client import McpClient, McpError
from src.native.tools import native_tools


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Python MCP agent for 01_04_z-task."
    )
    parser.add_argument(
        "--query",
        default=DEFAULT_QUERY,
        help="User query sent to the agent.",
    )
    parser.add_argument(
        "--server",
        default=DEFAULT_SERVER_NAME,
        help="Server name from mcp.json.",
    )
    return parser.parse_args()


async def async_main() -> int:
    args = parse_args()
    mcp_client: McpClient | None = None

    try:
        log.box("01_04_z-task\nPython MCP agent")
        log.start(f"Connecting to MCP server '{args.server}'...")

        mcp_client = McpClient()
        await mcp_client.connect(args.server)

        mcp_tools = await mcp_client.list_tools()
        log.success(
            "MCP: " + ", ".join(tool["name"] for tool in mcp_tools) if mcp_tools else "MCP: no tools"
        )
        log.success(
            "Native: " + ", ".join(tool["name"] for tool in native_tools)
        )

        log.start("Starting agent loop...")
        result = await run(args.query, mcp_client=mcp_client, mcp_tools=mcp_tools)

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


def main() -> int:
    try:
        return asyncio.run(async_main())
    except KeyboardInterrupt:
        log.warn("Interrupted")
        return 130


if __name__ == "__main__":
    sys.exit(main())