from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List

@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]

class MCPServerBase:

    def list_tools(self) -> List[ToolSpec]:
        raise NotImplementedError

    async def call_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError
