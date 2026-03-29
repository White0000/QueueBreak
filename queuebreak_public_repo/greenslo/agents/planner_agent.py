from __future__ import annotations
from typing import List
from greenslo.agents.types import Plan, ToolCall
from greenslo.orchestrator.green_slo_contract import GreenSLO
from greenslo.orchestrator.scheduler import PriorityBatchScheduler
from greenslo.utils.json import try_parse_json

class PlannerAgent:

    def __init__(self, scheduler: PriorityBatchScheduler) -> None:
        self.sched = scheduler

    def _heuristic_plan(self, workflow_type: str, sensor_id: str, device_id: str) -> Plan:
        if workflow_type == 'iot_triage':
            calls = [ToolCall(tool='sensor_read', args={'sensor_id': sensor_id, 'n': 8}), ToolCall(tool='anomaly_score', args={'values': '${sensor.values}'})]
        elif workflow_type == 'tool_fanout':
            calls = [ToolCall(tool='sensor_read', args={'sensor_id': sensor_id, 'n': 16}), ToolCall(tool='device_status', args={'device_id': device_id}), ToolCall(tool='anomaly_score', args={'values': '${sensor.values}'})]
        else:
            calls = [ToolCall(tool='sensor_read', args={'sensor_id': sensor_id, 'n': 12}), ToolCall(tool='anomaly_score', args={'values': '${sensor.values}'}), ToolCall(tool='device_status', args={'device_id': device_id})]
        return Plan(calls=calls, raw='heuristic', ok=True)

    async def plan(self, workflow_id: str, workflow_type: str, user_request: str, tools_brief: str, contract: GreenSLO, sensor_id: str, device_id: str) -> Plan:
        prompt = f'You are a tool-using planner.\nAvailable tools (name: description):\n{tools_brief}\n\nUser request:\n{user_request}\n\nReturn ONLY valid JSON with the following format:\n{{"calls":[{{"tool":"sensor_read","args":{{...}}}}, ...]}}\nRules:\n- Prefer at most 3 tool calls.\n- Always read a sensor first for IoT tasks.\n'
        try:
            res = await self.sched.submit(prompt, max_new_tokens=min(128, contract.max_new_tokens), contract=contract, meta={'workflow_id': workflow_id, 'step': 'planner'})
            obj = try_parse_json(res.text)
            if isinstance(obj, dict) and isinstance(obj.get('calls'), list):
                calls: List[ToolCall] = []
                for c in obj['calls']:
                    if not isinstance(c, dict):
                        continue
                    tool = str(c.get('tool', '')).strip()
                    args = c.get('args', {})
                    if tool and isinstance(args, dict):
                        calls.append(ToolCall(tool=tool, args=args))
                if calls:
                    return Plan(calls=calls, raw=res.text, ok=True, llm_tokens_in=res.tokens_in, llm_tokens_out=res.tokens_out, llm_start_t=res.start_t, llm_end_t=res.end_t, llm_energy_j=res.energy_j)
        except Exception:
            pass
        return self._heuristic_plan(workflow_type, sensor_id=sensor_id, device_id=device_id)
