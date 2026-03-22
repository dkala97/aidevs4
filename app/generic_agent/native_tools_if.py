from abc import ABC, abstractmethod
from typing import Any
from argparse import Namespace


class NativeToolsIf(ABC):
    @abstractmethod
    def list_tools(self) -> list[dict[str, Any]]:
        raise NotImplementedError()

    @abstractmethod
    def is_native_tool(self, name: str) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        raise NotImplementedError()

class NativeToolsFactoryIf(ABC):
    @abstractmethod
    def create_native_tools(self, args: Namespace) -> NativeToolsIf:
        raise NotImplementedError()


# Stubs
class NativeToolsStub(NativeToolsIf):
    def list_tools(self) -> list[dict[str, Any]]:
        return []

    def is_native_tool(self, name: str) -> bool:
        return False

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        return {}

class NativeToolsFactoryStub(NativeToolsFactoryIf):
    def create_native_tools(self, _) -> NativeToolsIf:
        return NativeToolsStub()
