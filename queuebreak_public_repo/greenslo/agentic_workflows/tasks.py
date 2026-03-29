from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict

@dataclass(frozen=True)
class WorkflowTask:
    workflow_id: str
    workflow_type: str
    sla_tier: str
    arrival_t: float
    user_request: str
    sensor_id: str = 'S1'
    device_id: str = 'D1'
    extra: Dict[str, Any] = None
