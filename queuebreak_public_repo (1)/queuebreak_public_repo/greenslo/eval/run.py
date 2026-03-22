from __future__ import annotations
import argparse
import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Tuple
import pandas as pd
from rich.console import Console
from rich.pretty import Pretty
from greenslo.agentic_workflows.generator import generate_tasks
from greenslo.eval.arrivals import generate_arrival_times
from greenslo.eval.metrics import summarize
from greenslo.eval.plots import plot_latency_cdf, plot_pareto
from greenslo.measurement.nvml_sampler import NVMLSampler
from greenslo.measurement.trace import StepRecord, WorkflowRecord
from greenslo.mcp.servers.iot_tools import IoTToolServer, ToolServerConfig
from greenslo.orchestrator.green_slo_contract import GreenSLO
from greenslo.orchestrator.llm_service import LLMService
from greenslo.orchestrator.orchestrator import Orchestrator
from greenslo.orchestrator.scheduler import PriorityBatchScheduler
from greenslo.utils.config import load_yaml
from greenslo.utils.seed import set_global_seed
console = Console()

def _load_contracts(slas_file: Path) -> Dict[str, GreenSLO]:
    slas = load_yaml(slas_file)
    tiers = slas.get('tiers', {})
    out: Dict[str, GreenSLO] = {}
    for tier, cfg in tiers.items():
        out[str(tier)] = GreenSLO.from_dict(str(tier), cfg)
    return out

def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', required=True, help='Path to experiment YAML')
    ap.add_argument('--workloads_dir', default='data/workloads', help='Where JSONL workload files are stored')
    args = ap.parse_args()
    cfg = load_yaml(Path(args.config))
    seed = int(cfg.get('seed', 42))
    set_global_seed(seed)
    models_file = Path(cfg['models_file'])
    slas_file = Path(cfg['slas_file'])
    models = load_yaml(models_file)
    contracts = _load_contracts(slas_file)
    use_fallback = bool(cfg.get('use_fallback_models', False))
    if use_fallback:
        planner_id = str(models['fallback']['model_id'])
        writer_id = str(models['fallback']['model_id'])
    else:
        planner_id = str(models['planner']['model_id'])
        writer_id = str(models['writer']['model_id'])
    mcfg = cfg.get('measurement', {})
    sampler = NVMLSampler(enable=bool(mcfg.get('enable_nvml', True)), sample_hz=int(mcfg.get('sample_hz', 20)))
    sampler.start()
    idle_s = float(mcfg.get('idle_baseline_seconds', 3))
    baseline = sampler.estimate_idle_baseline(seconds=idle_s)
    if baseline is None:
        console.print('[yellow]NVML baseline not available (no GPU power readings). Energy metrics will be None.[/yellow]')
    else:
        console.print(f'[green]Idle baseline power:[/green] {baseline:.2f} W')
    planner_llm = LLMService(model_id=planner_id)
    writer_llm = LLMService(model_id=writer_id)
    import asyncio
    gpu_lock = asyncio.Lock()
    planner_sched = PriorityBatchScheduler(llm=planner_llm, sampler=sampler, gpu_lock=gpu_lock, name='planner')
    writer_small_sched = PriorityBatchScheduler(llm=planner_llm, sampler=sampler, gpu_lock=gpu_lock, name='writer_small')
    writer_large_sched = PriorityBatchScheduler(llm=writer_llm, sampler=sampler, gpu_lock=gpu_lock, name='writer_large')
    tcfg = cfg.get('tools', {})
    tool_server = IoTToolServer(cfg=ToolServerConfig(base_latency_ms=int(tcfg.get('base_latency_ms', 60)), jitter_ms=int(tcfg.get('jitter_ms', 50)), failure_prob=float(tcfg.get('failure_prob', 0.15))), seed=seed)
    orch = Orchestrator(contracts=contracts, tool_server=tool_server, planner_sched=planner_sched, writer_small_sched=writer_small_sched, writer_large_sched=writer_large_sched)
    wcfg = cfg.get('workload', {})
    n = int(wcfg.get('n_workflows', 10))
    rate = float(wcfg.get('arrival_rate_rps', 1.0))
    burst = float(wcfg.get('burstiness', 1.0))
    mix = dict(wcfg.get('mix', {'iot_triage': 1.0}))
    tiers = list(wcfg.get('sla_tiers', ['balanced']))
    arrivals = generate_arrival_times(n=n, rate_rps=rate, burstiness=burst, seed=seed + 7)
    tasks = generate_tasks(n=n, arrival_times=arrivals, workflow_mix=mix, sla_tiers=tiers, workloads_dir=args.workloads_dir, seed=seed + 11)
    console.print(f"[cyan]Run:[/cyan] {cfg.get('run_name', 'run')} | workflows={n} | rate={rate} rps | burst={burst}")
    console.print(f'[cyan]Models:[/cyan] planner={planner_id} | writer={writer_id} | mock(planner)={planner_llm.is_mock} mock(writer)={writer_llm.is_mock}')

    async def _run_all() -> Tuple[List[WorkflowRecord], List[StepRecord], float]:
        exp_start = time.perf_counter()
        coros = [orch.run_workflow(t, exp_start_t=exp_start) for t in tasks]
        results = await asyncio.gather(*coros)
        workflows: List[WorkflowRecord] = []
        steps: List[StepRecord] = []
        for wf, st in results:
            workflows.append(wf)
            steps.extend(st)
        duration_s = max(0.001, max((w.end_t for w in workflows)) - exp_start) if workflows else 0.0
        return (workflows, steps, float(duration_s))
    workflows, steps, duration_s = asyncio.run(_run_all())
    sampler.stop()
    summary = summarize(workflows, duration_s=duration_s)
    console.print('\n[bold]Summary[/bold]')
    console.print(Pretty(summary))
    out_cfg = cfg.get('output', {})
    out_root = Path(out_cfg.get('out_dir', 'runs'))
    _ensure_dir(out_root)
    ts = time.strftime('%Y%m%d_%H%M%S')
    run_dir = out_root / f"{cfg.get('run_name', 'run')}_{ts}"
    _ensure_dir(run_dir)
    (run_dir / 'config_used.yaml').write_text(Path(args.config).read_text(encoding='utf-8'), encoding='utf-8')
    (run_dir / 'summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
    if bool(out_cfg.get('save_parquet', True)):
        try:
            df_w = pd.DataFrame([asdict(w) for w in workflows])
            df_s = pd.DataFrame([asdict(s) for s in steps])
            if 'extra' in df_w.columns:
                df_w['extra'] = df_w['extra'].apply(lambda x: json.dumps(x, ensure_ascii=False))
            if 'extra' in df_s.columns:
                df_s['extra'] = df_s['extra'].apply(lambda x: json.dumps(x, ensure_ascii=False))
            df_w.to_parquet(run_dir / 'workflows.parquet', index=False)
            df_s.to_parquet(run_dir / 'steps.parquet', index=False)
        except Exception as e:
            console.print(f'[yellow]Parquet save failed: {e}. Falling back to CSV.[/yellow]')
            df_w.to_csv(run_dir / 'workflows.csv', index=False)
            df_s.to_csv(run_dir / 'steps.csv', index=False)
    if bool(out_cfg.get('save_jsonl', True)):
        with (run_dir / 'workflows.jsonl').open('w', encoding='utf-8') as f:
            for w in workflows:
                f.write(json.dumps(asdict(w), ensure_ascii=False) + '\n')
        with (run_dir / 'steps.jsonl').open('w', encoding='utf-8') as f:
            for s in steps:
                f.write(json.dumps(asdict(s), ensure_ascii=False) + '\n')
    if bool(out_cfg.get('make_plots', True)):
        plot_pareto(workflows, run_dir / 'pareto_energy_latency.png')
        plot_latency_cdf(workflows, run_dir / 'latency_cdf.png')
    console.print(f'\n[green]Artifacts written to:[/green] {run_dir}')
if __name__ == '__main__':
    main()
