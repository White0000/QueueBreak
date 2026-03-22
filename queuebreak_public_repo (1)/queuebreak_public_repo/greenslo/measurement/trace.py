from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import time

@dataclass
class StepRecord:
    workflow_id: str
    step_id: str
    step_type: str
    model_or_tool: str
    start_t: float
    end_t: float
    latency_ms: float
    tokens_in: int = 0
    tokens_out: int = 0
    energy_j: Optional[float] = None
    ok: bool = True
    error: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WorkflowRecord:
    workflow_id: str
    workflow_type: str
    sla_tier: str
    arrival_t: float
    start_t: float
    end_t: float
    latency_ms: float
    energy_j: Optional[float]
    success: bool
    slo_latency_ok: bool
    slo_energy_ok: bool
    green_ok: bool
    error: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

def now() -> float:
    return time.perf_counter()
