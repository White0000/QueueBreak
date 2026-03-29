from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional

@dataclass
class RepairDecision:
    action: str
    tool: Optional[str] = None
    args: Optional[Dict[str, Any]] = None
    reason: str = ''

class RepairAgent:

    def decide(self, tool_name: str, args: Dict[str, Any], attempt: int, max_retries: int) -> RepairDecision:
        if attempt < max_retries:
            return RepairDecision(action='retry', tool=tool_name, args=args, reason='retry_within_budget')
        if tool_name == 'sensor_read':
            return RepairDecision(action='alternate', tool='device_status', args={'device_id': 'D1'}, reason='alternate_context')
        return RepairDecision(action='skip', reason='retry_budget_exhausted')
