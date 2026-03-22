"""
Native tools factory for failure log analysis task.
Integrates with generic_agent framework.
"""

from typing import Any
from argparse import Namespace

from src.native_tools import FailureLogAnalyzer

from generic_agent.native_tools_if import NativeToolsIf, NativeToolsFactoryIf
from generic_agent.config import AgentConfig


class FailureLogNativeTools(NativeToolsIf):
    """Native tools wrapper for failure log analysis."""

    def __init__(self, config: AgentConfig):
        self._analyzer = FailureLogAnalyzer(config)
        self._config = config

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "name": "download_logs",
                "description": "Download failure logs from HUB and save to workflow directory",
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
                "name": "filter_lines",
                "description": "Read a log file, filter lines based on regex pattern and write it to the output file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "input_path": {
                            "type": "string",
                            "description": "Path to the filtered log file.",
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Path to write the compressed output.",
                        },
                        "pattern": {
                            "type": "string",
                            "description": "Regex pattern to use for filtering. If line matches that pattern it will be preserved. Example: '.*(CRIT|ERR|WARN).*'",
                        },
                    },
                    "required": ["input_path", "output_path", "pattern"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
            {
                "type": "function",
                "name": "compress_logs",
                "description": "Read a filtered log file, shorten descriptions to fit within 1500 tokens, and write the result to an output file..",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "input_path": {
                            "type": "string",
                            "description": "Path to the input file.",
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Path to write the compressed output.",
                        },
                        "max_tokens": {
                            "type": "integer",
                            "description": "Maximum tokens allowed (default: 1500).",
                        },
                    },
                    "required": ["input_path", "output_path", "max_tokens"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
            {
                "type": "function",
                "name": "count_tokens",
                "description": "Count tokens in a file without loading its content into context.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file to count tokens for.",
                        },
                    },
                    "required": ["file_path"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
            {
                "type": "function",
                "name": "submit_to_centrala",
                "description": "Read compressed logs from a file and submit to Centrala for verification.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "logs_path": {
                            "type": "string",
                            "description": "Path to the log file.",
                        },
                    },
                    "required": ["logs_path"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
        ]

    def is_native_tool(self, name: str) -> bool:
        return name in ["download_logs", "filter_lines", "compress_logs", "count_tokens", "submit_to_centrala"]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        if name == "download_logs":
            result = await self._analyzer.download_logs()
            return result

        elif name == "filter_lines":
            result = self._analyzer.filter_lines(
                input_path=arguments["input_path"],
                output_path=arguments["output_path"],
                pattern=arguments["pattern"],
            )
            return result

        elif name == "compress_logs":
            result = await self._analyzer.compress_logs(
                input_path=arguments["input_path"],
                output_path=arguments["output_path"],
                max_tokens=arguments["max_tokens"],
            )
            return result

        elif name == "count_tokens":
            result = self._analyzer.count_tokens_file(arguments["file_path"])
            return result

        elif name == "submit_to_centrala":
            result = await self._analyzer.submit_to_centrala(arguments["logs_path"])
            return result

        else:
            return f"Error: Unknown tool: {name}"


class FailureLogNativeToolsFactory(NativeToolsFactoryIf):
    def __init__(self, config: AgentConfig):
        self._config = config

    def create_native_tools(self, _: Namespace) -> NativeToolsIf:
        return FailureLogNativeTools(self._config)
