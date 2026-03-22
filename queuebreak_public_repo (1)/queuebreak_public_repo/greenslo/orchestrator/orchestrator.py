from __future__ import annotations
import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple
from greenslo.agentic_workflows.tasks import WorkflowTask
from greenslo.agents.planner_agent import PlannerAgent
from greenslo.agents.repair_agent import RepairAgent
from greenslo.agents.writer_agent import WriterAgent
from greenslo.measurement.trace import StepRecord, WorkflowRecord, now
from greenslo.mcp.servers.iot_tools import IoTToolServer
from greenslo.orchestrator.green_slo_contract import GreenSLO
from greenslo.orchestrator.router import GreenRouter
from greenslo.orchestrator.scheduler import PriorityBatchScheduler

class Orchestrator:

    def __init__(self, contracts: Dict[str, GreenSLO], tool_server: IoTToolServer, planner_sched: PriorityBatchScheduler, writer_small_sched: PriorityBatchScheduler, writer_large_sched: PriorityBatchScheduler) -> None:
        self.contracts = contracts
        self.tool_server = tool_server
        self.planner = PlannerAgent(planner_sched)
        self.repair = RepairAgent()
        self.router = GreenRouter(small_sched=writer_small_sched, large_sched=writer_large_sched)
        self.writer = WriterAgent(router=self.router)
        brief_lines = []
        for t in self.tool_server.list_tools():
            brief_lines.append(f'- {t.name}: {t.description}')
        self._tools_brief = '\n'.join(brief_lines)

    async def _call_tool_with_repair(self, task: WorkflowTask, contract: GreenSLO, tool_name: str, args: Dict[str, Any], step_records: List[StepRecord], step_id_prefix: str) -> Optional[Dict[str, Any]]:
        attempts = 0
        while True:
            attempts += 1
            step_id = f'{step_id_prefix}_{attempts}'
            t0 = now()
            try:
                out = await self.tool_server.call_tool(tool_name, args)
                t1 = now()
                step_records.append(StepRecord(workflow_id=task.workflow_id, step_id=step_id, step_type='tool', model_or_tool=tool_name, start_t=t0, end_t=t1, latency_ms=(t1 - t0) * 1000.0, ok=True, extra={'args': args}))
                return out
            except Exception as e:
                t1 = now()
                step_records.append(StepRecord(workflow_id=task.workflow_id, step_id=step_id, step_type='tool', model_or_tool=tool_name, start_t=t0, end_t=t1, latency_ms=(t1 - t0) * 1000.0, ok=False, error=str(e), extra={'args': args}))
                decision = self.repair.decide(tool_name, args, attempt=attempts, max_retries=contract.max_retries)
                if decision.action in {'retry', 'alternate'} and decision.tool and decision.args:
                    tool_name, args = (decision.tool, decision.args)
                    continue
                return None

    async def run_workflow(self, task: WorkflowTask, exp_start_t: float) -> Tuple[WorkflowRecord, List[StepRecord]]:
        contract = self.contracts[task.sla_tier]
        step_records: List[StepRecord] = []
        arrival_abs = exp_start_t + task.arrival_t
        await asyncio.sleep(max(0.0, arrival_abs - time.perf_counter()))
        wf_start = now()
        error: Optional[str] = None
        tool_results: Dict[str, Any] = {}
        energy_accum: Optional[float] = 0.0
        remaining_energy = float(contract.energy_j_budget)

        def add_energy(e: Optional[float]) -> None:
            nonlocal energy_accum, remaining_energy
            if energy_accum is None:
                return
            if e is None:
                energy_accum = None
                return
            energy_accum += float(e)
            remaining_energy -= float(e)
        plan = await self.planner.plan(workflow_id=task.workflow_id, workflow_type=task.workflow_type, user_request=task.user_request, tools_brief=self._tools_brief, contract=contract, sensor_id=task.sensor_id, device_id=task.device_id)
        if plan.llm_start_t is not None and plan.llm_end_t is not None:
            step_records.append(StepRecord(workflow_id=task.workflow_id, step_id='planner', step_type='planner', model_or_tool='planner_model', start_t=float(plan.llm_start_t), end_t=float(plan.llm_end_t), latency_ms=(float(plan.llm_end_t) - float(plan.llm_start_t)) * 1000.0, tokens_in=int(plan.llm_tokens_in), tokens_out=int(plan.llm_tokens_out), energy_j=plan.llm_energy_j, ok=bool(plan.ok), extra={'raw': plan.raw}))
            add_energy(plan.llm_energy_j)
        tool_calls_used = 0
        for idx, call in enumerate(plan.calls[:contract.max_tool_calls]):
            tool_calls_used += 1
            tool_name = call.tool
            args = dict(call.args)
            if tool_name == 'anomaly_score' and isinstance(args.get('values'), str) and (args.get('values') == '${sensor.values}'):
                sensor = tool_results.get('sensor_read')
                if isinstance(sensor, dict) and 'values' in sensor:
                    args['values'] = sensor['values']
                else:
                    args['values'] = []
            if tool_name == 'sensor_read':
                args.setdefault('sensor_id', task.sensor_id)
            if tool_name == 'device_status':
                args.setdefault('device_id', task.device_id)
            out = await self._call_tool_with_repair(task=task, contract=contract, tool_name=tool_name, args=args, step_records=step_records, step_id_prefix=f'tool_{idx}_{tool_name}')
            if out is None:
                error = f'tool_failed:{tool_name}'
                break
            tool_results[tool_name] = out
        writer_res = None
        if error is None:
            rem = remaining_energy if energy_accum is not None else None
            try:
                writer_res = await self.writer.write(workflow_id=task.workflow_id, user_request=task.user_request, tool_results=tool_results, contract=contract, remaining_energy_j=rem)
                tool_results['writer_output'] = writer_res.obj
            except Exception as e:
                error = f'writer_failed:{e}'
        if writer_res is not None and writer_res.llm_start_t is not None and (writer_res.llm_end_t is not None):
            step_records.append(StepRecord(workflow_id=task.workflow_id, step_id='writer', step_type='writer', model_or_tool='writer_model', start_t=float(writer_res.llm_start_t), end_t=float(writer_res.llm_end_t), latency_ms=(float(writer_res.llm_end_t) - float(writer_res.llm_start_t)) * 1000.0, tokens_in=int(writer_res.llm_tokens_in), tokens_out=int(writer_res.llm_tokens_out), energy_j=writer_res.llm_energy_j, ok=bool(writer_res.ok), extra={'raw': writer_res.raw, 'route_reason': writer_res.route_reason}))
            add_energy(writer_res.llm_energy_j)
        if error is None:
            action = None
            try:
                action = str(tool_results.get('writer_output', {}).get('action', '')).upper()
            except Exception:
                action = None
            if action in {'THROTTLE', 'REBOOT'} and tool_calls_used < contract.max_tool_calls:
                out = await self._call_tool_with_repair(task=task, contract=contract, tool_name='actuate', args={'device_id': task.device_id, 'action': action.lower()}, step_records=step_records, step_id_prefix='tool_actuate')
                if out is not None:
                    tool_results['actuate'] = out
        wf_end = now()
        latency_ms = (wf_end - wf_start) * 1000.0
        e_total = None if energy_accum is None else float(energy_accum)
        success = error is None
        slo_latency_ok = latency_ms <= float(contract.p99_ms)
        slo_energy_ok = True if e_total is None else e_total <= float(contract.energy_j_budget)
        green_ok = bool(success and slo_latency_ok and slo_energy_ok)
        wf_rec = WorkflowRecord(workflow_id=task.workflow_id, workflow_type=task.workflow_type, sla_tier=task.sla_tier, arrival_t=float(task.arrival_t), start_t=wf_start, end_t=wf_end, latency_ms=float(latency_ms), energy_j=e_total, success=bool(success), slo_latency_ok=bool(slo_latency_ok), slo_energy_ok=bool(slo_energy_ok), green_ok=bool(green_ok), error=error, extra={'tool_results': tool_results})
        return (wf_rec, step_records)
