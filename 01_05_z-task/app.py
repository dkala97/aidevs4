#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import sys

from src.agent import run
from src.logger import log


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Python agent for auto-api."
    )
    parser.add_argument(
        "--query",
        required=True,
        help="User query sent to the agent.",
    )
    return parser.parse_args()


async def async_main() -> int:
    args = parse_args()

    try:
        log.box("Python agent supporting auto-api.")
        log.start("Starting agent loop...")

        result = await run(args.query)

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