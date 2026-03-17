from __future__ import annotations

import csv
import json
from io import StringIO
from typing import Any

import requests
from ..config import HUB_API_KEY, HUB_URL, PROJECT_ROOT
from ..logger import log


# Define native tools
native_tools = [
    {
        "type": "function",
        "name": "reset",
        "description": "Reset the agent state for a new test. Call this when preparing for a new test, after budget exceeded, or after test_prompt error.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "fetch_data",
        "description": "Fetch task data. Call this before writing a new prompt to retrieve the latest task data.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "test_prompt",
        "description": "Test a prompt against the task. Returns success with flag on correct solution, or error message with hint on failure.",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The prompt to test.",
                },
            },
            "required": ["prompt"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


def is_native_tool(name: str) -> bool:
    """Check if the tool is a native tool."""
    return name in {"reset", "fetch_data", "test_prompt"}


async def execute_native_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute a native tool."""
    if name == "reset":
        return await reset()
    elif name == "fetch_data":
        return await fetch_data()
    elif name == "test_prompt":
        prompt = arguments.get("prompt")
        if not prompt:
            return {"error": "prompt parameter is required"}
        return await test_prompt(prompt)
    else:
        raise RuntimeError(f"Unknown native tool: {name}")


async def reset() -> dict[str, Any]:
    """Reset tool implementation - calls HUB API to reset task state."""

    if not HUB_URL or not HUB_API_KEY:
        return {"error": "HUB_URL or HUB_API_KEY not configured"}

    try:
        payload = {
            "apikey": HUB_API_KEY,
            "task": "categorize",
            "answer": {"prompt": "reset"},
        }
        log.http_request("POST", f"{HUB_URL}/verify", payload)

        response = requests.post(
            f"{HUB_URL}/verify",
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
        log.http_response(response.status_code, True, result)
        return result
    except Exception as error:
        log.http_response(getattr(response, "status_code", 0), False, str(error))
        return {"error": str(error)}


async def fetch_data() -> dict[str, Any]:
    """Fetch data tool implementation - downloads task data CSV and parses to JSON."""

    if not HUB_URL or not HUB_API_KEY:
        return {"error": "HUB_URL or HUB_API_KEY not configured"}

    try:
        url = f"{HUB_URL}/data/{HUB_API_KEY}/categorize.csv"
        log.http_request("GET", url)

        response = requests.get(url, timeout=30)
        response.raise_for_status()
        log.http_response(response.status_code, True, f"Downloaded {len(response.content)} bytes")

        # Parse CSV to JSON
        csv_text = response.content.decode("utf-8")
        csv_reader = csv.DictReader(StringIO(csv_text))
        data = list(csv_reader)

        output_path = PROJECT_ROOT / "data" / "categorize.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        return {
            "status": "success",
            "data": data,
        }
    except Exception as error:
        log.http_response(getattr(response, "status_code", 0), False, str(error))
        return {"error": str(error)}


async def test_prompt(prompt: str) -> dict[str, Any]:
    """Test prompt tool implementation - tests prompt against each data item."""
    if not HUB_URL or not HUB_API_KEY:
        return {"error": "HUB_URL or HUB_API_KEY not configured"}

    try:
        # Load the data file
        data_path = PROJECT_ROOT / "data" / "categorize.json"
        if not data_path.exists():
            return {"error": f"Data file not found: {data_path}"}

        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        status = "success"
        # Test prompt against each item
        for item in data:
            code = item.get("code", "")
            description = item.get("description", "")
            full_prompt = f"{prompt}\nCode: {code}, Description: {description}" if code else prompt

            try:
                payload = {
                    "apikey": HUB_API_KEY,
                    "task": "categorize",
                    "answer": {"prompt": full_prompt},
                }
                log.http_request("POST", f"{HUB_URL}/verify", payload)

                response = requests.post(
                    f"{HUB_URL}/verify",
                    json=payload,
                    timeout=30,
                )
                response.raise_for_status()
                result = response.json()
                log.http_response(response.status_code, True, result)
                item["result"] = result
            except Exception as error:
                log.http_response(getattr(response, "status_code", 0), False, str(error))
                item["result"] = {"error": str(error)}
                status = "error"

        return {
            "status": status,
            "data": data,
        }
    except Exception as error:
        return {"error": str(error)}
