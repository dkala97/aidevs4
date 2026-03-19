#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import sys

from src.agent import run
from src.logger import log
from src.native.tools import native_tools


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Python agent for 02_02_z-task."
    )
    parser.add_argument(
        "--query",
        default=None,
        help="User query sent to the agent.",
    )
    parser.add_argument(
        "--query_file",
        help="Path to query file"
    )
    return parser.parse_args()


async def async_main() -> int:
    args = parse_args()

    try:
        log.box("02_02_z-task\nPython agent")

        log.success(
            "Native: " + ", ".join(tool["name"] for tool in native_tools)
        )

        query=args.query
        if not query:
            with open(args.query_file) as f:
                query=f.read()
        if not query:
            raise ValueError("Missing query")

        log.start("Starting agent loop...")
        result = await run(query)

        log.success("Agent finished")
        print()
        print(result["response"])
        return 0
    except (RuntimeError, ValueError) as error:
        log.error("Startup error", str(error))
        return 1


def main() -> int:
    try:
        return asyncio.run(async_main())
    except KeyboardInterrupt:
        log.warn("Interrupted")
        return 130


if __name__ == "__main__":
    sys.exit(main())