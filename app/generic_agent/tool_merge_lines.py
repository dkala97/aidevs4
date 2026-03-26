from __future__ import annotations

from typing import Any

from .config import AgentConfig
from .logger import log
from .utils import resolve_workspace_path

def create_tool_schema_merge_lines(tool_name: str = "merge_lines"):
    return {
        "type": "function",
        "name": tool_name,
        "description": "Merge lines from input files into output file. Optionally, remove duplicates from output file.",
        "parameters": {
            "type": "object",
            "properties": {
                "input_files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of input files to read lines from and merge",
                },
                "output_file": {
                    "type": "string",
                    "description": "Path to the file where output lines shall be saved"
                },
                "unique_lines": {
                    "type": "boolean",
                    "description": "Optional parameter. Set to `true` to remove duplicate lines from the output file. Default: `false`."
                }
            },
            "required": ["input_files", "output_file"],
            "additionalProperties": False,
        },
        "strict": True,
    }

class ToolMergeLines:
    def __init__(self, shared_config: AgentConfig):
        self._shared_config = shared_config

    async def call(self, params: dict[str, Any]) ->Any:
        if "input_files" not in params:
            return { "status": "error: Missing required parameter: input_files: list[str]" }
        if "output_file" not in params:
            return { "status": "error: Missing required parameter: output_file: str" }
        input_filepaths=params["input_files"]
        output_filepath=params["output_file"]
        unique_lines= params["unique_lines"] if "unique_lines" in params else False

        lines: list[str] | set[str] = [] if unique_lines else set()
        counters: list[int] = []

        try:
            for input_filepath in input_filepaths:
                with resolve_workspace_path(self._shared_config, input_filepath).open() as input_file:
                    file_lines=input_file.read().split("\n")
                    counters.append(len(file_lines))
                    lines.extend(file_lines)

            with resolve_workspace_path(self._shared_config, output_filepath).open("w") as output_file:
                output_file.write("\n".join(lines))
        except Exception as ex:
            return {"status": f"error: {ex}"}

        status = f"Merged: {counters} liens from input files into {len(lines)} output lines"
        log.info(status)
        return {"status": status}
