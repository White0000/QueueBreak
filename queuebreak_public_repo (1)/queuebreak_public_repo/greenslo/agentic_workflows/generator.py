from __future__ import annotations
import random
from pathlib import Path
from typing import Dict, List
from greenslo.agentic_workflows.tasks import WorkflowTask

def _load_jsonl_texts(path: Path, text_keys: List[str], limit: int=500) -> List[str]:
    if not path.exists():
        return []
    out: List[str] = []
    import json
    with path.open('r', encoding='utf-8') as f:
        for line in f:
            if len(out) >= limit:
                break
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                for k in text_keys:
                    if k in obj and isinstance(obj[k], str) and obj[k].strip():
                        out.append(obj[k].strip())
                        break
            except Exception:
                continue
    return out

def build_prompt_bank(workloads_dir: str | Path) -> Dict[str, List[str]]:
    d = Path(workloads_dir)
    bank: Dict[str, List[str]] = {}
    bank['news'] = _load_jsonl_texts(d / 'ag_news.jsonl', ['text', 'title'], limit=800)
    bank['dialogue'] = _load_jsonl_texts(d / 'samsum.jsonl', ['dialogue'], limit=800)
    bank['code'] = _load_jsonl_texts(d / 'mbpp.jsonl', ['text'], limit=800)
    return bank

def synthesize_user_request(rng: random.Random, bank: Dict[str, List[str]]) -> str:
    snippets: List[str] = []
    if bank.get('news') and rng.random() < 0.3:
        snippets.append(rng.choice(bank['news'])[:180])
    if bank.get('dialogue') and rng.random() < 0.3:
        snippets.append(rng.choice(bank['dialogue'])[:180])
    if bank.get('code') and rng.random() < 0.2:
        snippets.append(rng.choice(bank['code'])[:120])
    context = ' '.join(snippets).strip()
    if not context:
        context = 'A remote sensor reports intermittent spikes. The operator needs a decision under latency and energy budgets.'
    return 'IoT incident triage request: ' + context + '\nUse available tools to read sensor data, estimate anomaly, and recommend an action.'

def generate_tasks(n: int, arrival_times: List[float], workflow_mix: Dict[str, float], sla_tiers: List[str], workloads_dir: str | Path, seed: int) -> List[WorkflowTask]:
    rng = random.Random(seed)
    bank = build_prompt_bank(workloads_dir)
    keys = list(workflow_mix.keys())
    probs = [float(workflow_mix[k]) for k in keys]
    s = sum(probs) or 1.0
    probs = [p / s for p in probs]
    tasks: List[WorkflowTask] = []
    for i in range(n):
        wf_type = rng.choices(keys, weights=probs, k=1)[0]
        tier = rng.choice(list(sla_tiers))
        user_request = synthesize_user_request(rng, bank)
        sensor_id = f'S{1 + i % 5}'
        device_id = f'D{1 + i % 3}'
        tasks.append(WorkflowTask(workflow_id=f'wf_{i:05d}', workflow_type=wf_type, sla_tier=tier, arrival_t=float(arrival_times[i]), user_request=user_request, sensor_id=sensor_id, device_id=device_id, extra={}))
    return tasks
