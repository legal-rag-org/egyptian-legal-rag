from .ToolInterface import ToolInterface


class ToolRegistry:

    def __init__(self):
        self.tools: dict[str, ToolInterface] = {}

    def register(self, tool: ToolInterface):
        self.tools[tool.name] = tool

    def get(self, name: str) -> ToolInterface | None:
        return self.tools.get(name)

    def get_all(self) -> list[ToolInterface]:
        return list(self.tools.values())

    def get_schemas(self) -> list[dict]:
        return [
            tool.schema
            for tool in self.tools.values()
        ]