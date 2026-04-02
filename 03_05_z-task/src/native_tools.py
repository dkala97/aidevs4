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
            "tool_proxy": ToolAutoApi(ToolAutoApiConfig(
                endpoint=f"{HUB_URL}",
                payload_prototype={
                    "apikey": HUB_API_KEY
                }
            ), endpoint_url_decorator=self.tool_proxy_url_decorator),
            "sleep": ToolSleep()
        }

    def tool_proxy_url_decorator(self, params: dict[str, Any], endpoint_url):
        tool_url = params["url"]
        params_modified = {k: v for k, v in params.items() if k != "url"}
        return params_modified, f"{endpoint_url}{tool_url}"

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            create_tool_schema_auto_api(tool_name="verify", description=(
                "Tool used for verification of task solution. "
                "Provide `answer` object with task defined properties that SHALL be included into response. "
                "Returns verification response."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "Array with vehicle_name and driving instructions. vehicle_name at the first position followed by the list of directions. Possible directions: up, right, down left."
                    }
                },
                "required": ["answer"],
                "additionalProperties": False,
            }),
            create_tool_schema_auto_api(tool_name="tool_proxy", description=(
                "Tool used as a proxy for other tools available on remote server. "
                "To find remote tools for the current needs, use toolsearch available at url: `/api/toolsearch` and provide description as keywords or in natural language what tools you are looking for in the `query` property. "
                "Returns error description or tool output. "
            ),
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Remote tool endpoint url address."
                    },
                    "query": {
                        "type": "string",
                        "description": "Input query for the remote tool."
                    }
                },
                "required": ["url", "query"],
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
