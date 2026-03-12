#!/usr/bin/env python3
from __future__ import annotations

import sys

from src.assistant import ProxyAssistant
from src.config import SERVER_HOST, SERVER_PORT
from src.http_server import run_http_server
from src.logging_utils import log
from src.mcp_client import McpError, ParcelsMcpClient


def main() -> int:
    mcp: ParcelsMcpClient | None = None
    try:
        mcp = ParcelsMcpClient()
        mcp.start()

        assistant = ProxyAssistant(mcp)
        run_http_server(SERVER_HOST, SERVER_PORT, assistant)
        return 0
    except McpError as error:
        log(f"MCP setup failed: {error}")
        return 1
    except KeyboardInterrupt:
        log("Shutting down...")
        return 0
    finally:
        if mcp:
            mcp.close()


if __name__ == "__main__":
    sys.exit(main())
