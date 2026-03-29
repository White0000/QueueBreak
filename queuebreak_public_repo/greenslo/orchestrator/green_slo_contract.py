from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict

@dataclass(frozen=True)
class GreenSLO:
    tier: str
    p99_ms: int
    energy_j_budget: float
    waiting_window_ms: int
    max_batch_size: int
    max_batch_tokens: int
    max_tool_calls: int
    max_llm_calls: int
    max_new_tokens: int
    max_retries: int

    @staticmethod
    def from_dict(tier: str, d: Dict[str, Any]) -> 'GreenSLO':
        return GreenSLO(tier=tier, p99_ms=int(d['p99_ms']), energy_j_budget=float(d['energy_j_budget']), waiting_window_ms=int(d['waiting_window_ms']), max_batch_size=int(d['max_batch_size']), max_batch_tokens=int(d['max_batch_tokens']), max_tool_calls=int(d['max_tool_calls']), max_llm_calls=int(d['max_llm_calls']), max_new_tokens=int(d['max_new_tokens']), max_retries=int(d['max_retries']))
