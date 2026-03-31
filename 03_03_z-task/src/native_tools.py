from typing import Any
from argparse import Namespace

from generic_agent.config import AgentConfig
from generic_agent.native_tools_if import NativeToolsIf, NativeToolsFactoryIf
from generic_agent.tool_auto_api import ToolAutoApi, ToolAutoApiConfig, create_tool_schema_auto_api
from generic_agent.tool_sleep import ToolSleep, create_tool_schema_sleep

from .config import (
    HUB_URL,
    HUB_API_KEY,
    TASK_NAME
)

class TaskNativeTools(NativeToolsIf):
    def __init__(self, shared_config: AgentConfig):
        self._tools = {
            "verify": ToolAutoApi(ToolAutoApiConfig(
                endpoint=f"{HUB_URL}/verify",
                payload_prototype={
                    "apikey": HUB_API_KEY,
                    "task": TASK_NAME
                }
            )),
            "sleep": ToolSleep()
        }

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            create_tool_schema_auto_api(tool_name="verify", description=(
                "Tool used for executing commands."
                "Provide `answer` object with task defined properties that SHALL be included into request. "
                "Returns verification response."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "object",
                        "description": "Answer object containing command to be executed.",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "Command to be executed. One of: `start`, `reset`, `left`, `wait` and `right`"
                            }
                        },
                        "required": ["command"]
                    }
                },
                "required": ["answer"],
                "additionalProperties": False,
            }),
            create_tool_schema_sleep(tool_name="sleep")
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
