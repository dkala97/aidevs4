from typing import Any
from argparse import Namespace

from generic_agent.native_tools_if import NativeToolsIf, NativeToolsFactoryIf
from generic_agent.tool_auto_api import ToolAutoApi, ToolAutoApiConfig, create_tool_schema_auto_api
from generic_agent.tool_sleep import ToolSleep, create_tool_schema_sleep

from .config import (
    HUB_URL,
    HUB_API_KEY,
    TASK_NAME
)

class TaskNativeTools(NativeToolsIf):
    def __init__(self):
        self._tools = {
            "zmail":  ToolAutoApi(ToolAutoApiConfig(
                endpoint=f"{HUB_URL}/api/zmail",
                payload_prototype={
                    "apikey": HUB_API_KEY
                }
            )),
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
            create_tool_schema_auto_api(tool_name="zmail", description=(
                "E-Mail API working as GMail search tool. Allows for executing defined actions. "
                "To discover all possible actions and their parameters use help action. Call zmail({\"action\": \"help\"}). "
                "If the action requires additional arguments, provide them as follows: "
                "{\"action\":\"someaction\",\"actionarg1\":\"example\"}. "
                "Returns API response."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Action name to execute"
                    }
                },
                "required": ["action"],
                "additionalProperties": True,
            }),
            create_tool_schema_auto_api(tool_name="verify", description=(
                "Tool used for verification of task solution. "
                "Provide answer object with task defined properties that SHALL be included into response. "
                "Returns verification response."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "object",
                        "description": "Answer object to be verified by backend."
                    }
                },
                "required": ["answer"],
                "additionalProperties": True,
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
    def create_native_tools(self, _: Namespace) -> NativeToolsIf:
        return TaskNativeTools()
