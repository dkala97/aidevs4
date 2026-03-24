from __future__ import annotations

import asyncio
from typing import Any

from .logger import log

def create_tool_schema_sleep(tool_name: str = "sleep"):
    return {
        "type": "function",
        "name": tool_name,
        "description": "Pause execution for a number of seconds (float). Maximum is 60 seconds.",
        "parameters": {
            "type": "object",
            "properties": {
                "seconds": {
                    "type": "number",
                    "description": "Number of seconds to sleep. Must be between 0 and 60.",
                }
            },
            "required": ["seconds"],
            "additionalProperties": False,
        },
        "strict": True,
    }

class ToolSleep:
    async def call(self, params: dict[str, Any]) ->Any:
        if "seconds" not in params:
            return { "status": "error: Missing required parameter: seconds: float" }
        value = float(params["seconds"])
        if value < 0:
            return { "status": "error: seconds must be >= 0" }
        if value > 60:
            return { "status": "error: seconds must be <= 60" }

        log.info(f"Sleep for {value}")
        await asyncio.sleep(value)
        status = f"Sleep done, slept for {value} seconds"
        log.info(status)
        return {"status": status}
