from typing import Any
from argparse import Namespace

from generic_agent.config import AgentConfig
from generic_agent.utils import resolve_workspace_path
from generic_agent.native_tools_if import NativeToolsIf, NativeToolsFactoryIf
from generic_agent.tool_auto_api import ToolAutoApi, ToolAutoApiConfig, create_tool_schema_auto_api
from generic_agent.tool_sleep import ToolSleep, create_tool_schema_sleep
from generic_agent.tool_merge_lines import ToolMergeLines, create_tool_schema_merge_lines
from .tool_check_notes import ToolCheckNotes, create_tool_schema_check_notes
from .tool_check_ranges import ToolCheckRanges, create_tool_schema_check_ranges

from .config import (
    HUB_URL,
    HUB_API_KEY,
    TASK_NAME
)

class TaskNativeTools(NativeToolsIf):
    def __init__(self, shared_config: AgentConfig):
        self._shared_config = shared_config
        self._tools = {
            "verify": ToolAutoApi(ToolAutoApiConfig(
                endpoint=f"{HUB_URL}/verify",
                payload_prototype={
                    "apikey": HUB_API_KEY,
                    "task": TASK_NAME
                }
            ), params_decorator=self._load_result_file),
            "sleep": ToolSleep(),
            "check_notes": ToolCheckNotes(shared_config),
            "check_ranges": ToolCheckRanges(shared_config),
            "merge_lines": ToolMergeLines(shared_config)
        }

    def _load_result_file(self, verify_tool_params):
        if "result_filepath" not in verify_tool_params:
            raise RuntimeError("Missing parameter `result_filepath`")
        with resolve_workspace_path(self._shared_config, verify_tool_params["result_filepath"]).open() as result_file:
            return {
                "answer": {
                    "recheck": result_file.read().split("\n")
                }
            }

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            create_tool_schema_auto_api(tool_name="verify", description=(
                "Tool used for verification of task solution. "
                "Returns verification response."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "result_filepath": {
                        "type": "string",
                        "description": "Path to the file with data to be verified"
                    }
                },
                "required": ["result_filepath"],
                "additionalProperties": True,
            }),
            create_tool_schema_sleep(tool_name="sleep"),
            create_tool_schema_check_notes(tool_name="check_notes"),
            create_tool_schema_check_ranges(tool_name="check_ranges"),
            create_tool_schema_merge_lines(tool_name="merge_lines")
        ]

    def is_native_tool(self, name: str) -> bool:
        return name in self._tools

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        if self.is_native_tool(name):
            return await self._tools[name].call(arguments)
        else:
            return f"Error: Unknown tool: {name}"

class TaskNativeToolsFactory(NativeToolsFactoryIf):
    def __init__(self, shared_config: AgentConfig):
        self._shared_config = shared_config

    def create_native_tools(self, _: Namespace) -> NativeToolsIf:
        return TaskNativeTools(self._shared_config)
