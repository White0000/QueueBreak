from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

@dataclass(frozen=True)
class ToolCall:
    tool: str
    args: Dict[str, Any]

@dataclass
class Plan:
    calls: List[ToolCall]
    raw: str
    ok: bool
    llm_tokens_in: int = 0
    llm_tokens_out: int = 0
    llm_start_t: Optional[float] = None
    llm_end_t: Optional[float] = None
    llm_energy_j: Optional[float] = None

@dataclass
class WriterResult:
    obj: Dict[str, Any]
    raw: str
    ok: bool
    llm_tokens_in: int = 0
    llm_tokens_out: int = 0
    llm_start_t: Optional[float] = None
    llm_end_t: Optional[float] = None
    llm_energy_j: Optional[float] = None
    route_reason: str = ''
