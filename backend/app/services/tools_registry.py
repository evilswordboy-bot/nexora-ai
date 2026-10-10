from typing import Callable, Dict, Any, List, Optional
from pydantic import BaseModel, Field


class ToolDefinition(BaseModel):
    name: str = Field(..., description="Unique tool identifier")
    description: str = Field(..., description="Description of the tool function")
    parameters_schema: Dict[str, Any] = Field(..., description="JSON Schema for parameters")
    enabled: bool = True
    stage_introduced: int = 1


class ToolRegistry:
    """
    Extensible Tool Registry for NEXORA AI platform.
    Designed for progressive activation across 100 phases.
    """

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._handlers: Dict[str, Callable] = {}
        self._register_foundation_tools()

    def _register_foundation_tools(self):
        # Foundation diagnostic and system introspection tool
        self.register(
            tool=ToolDefinition(
                name="get_system_telemetry",
                description="Returns current Nexora platform telemetry, phase status, and active provider info.",
                parameters_schema={"type": "object", "properties": {}},
                stage_introduced=1,
            ),
            handler=self._handle_telemetry,
        )

    def register(self, tool: ToolDefinition, handler: Optional[Callable] = None):
        self._tools[tool.name] = tool
        if handler:
            self._handlers[tool.name] = handler

    def list_tools(self) -> List[ToolDefinition]:
        return list(self._tools.values())

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    async def execute(self, name: str, params: Dict[str, Any]) -> Any:
        if name not in self._handlers:
            raise ValueError(f"Tool '{name}' has no registered execution handler.")
        handler = self._handlers[name]
        return await handler(params)

    async def _handle_telemetry(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "platform": "NEXORA AI",
            "current_stage": 1,
            "architecture": "Universal Multi-Provider Assistant",
            "status": "operational",
        }


tool_registry = ToolRegistry()
