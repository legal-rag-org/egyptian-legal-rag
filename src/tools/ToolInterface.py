from abc import ABC, abstractmethod
from typing import Any
from services.AgentService import AgentContext

class ToolInterface(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        pass

    @property
    @abstractmethod
    def schema(self) -> dict:
        pass

    async def execute_with_context(self, arguments: dict, context: AgentContext) -> dict:

        return await self.execute(**arguments)