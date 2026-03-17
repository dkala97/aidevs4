#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import sys

from src.agent import run
from src.logger import log


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Python agent for 02_01_z-task."
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
        log.box("02_01_z-task\nPython Agent with Native Tools")
        log.start("Starting agent loop...")

        query=args.query
        if not query:
            with open(args.query_file) as f:
                query=f.read()
        if not query:
            raise ValueError("Missing query")

        result = await run(query)

        log.success("Agent finished")
        print()
        print(result["response"])
        return 0
    except (RuntimeError, ValueError) as error:
        log.error("Startup error", str(error))
        return 1
    except KeyboardInterrupt:
        log.warn("Interrupted")
        return 130


def main() -> int:
    try:
        return asyncio.run(async_main())
    except KeyboardInterrupt:
        log.warn("Interrupted")
        return 130


if __name__ == "__main__":
    sys.exit(main())
