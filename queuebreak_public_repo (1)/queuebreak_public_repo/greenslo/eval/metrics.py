from __future__ import annotations
from typing import Any, Dict, List
import numpy as np
from greenslo.measurement.trace import WorkflowRecord

def _pct(x: List[float], q: float) -> float:
    if not x:
        return float('nan')
    return float(np.percentile(np.array(x, dtype=float), q))

def summarize(workflows: List[WorkflowRecord], duration_s: float) -> Dict[str, Any]:
    lat = [w.latency_ms for w in workflows]
    energy = [w.energy_j for w in workflows if w.energy_j is not None]
    ok = [w for w in workflows if w.green_ok]
    goodput = len(ok) / max(1e-09, duration_s)
    out: Dict[str, Any] = {'n': len(workflows), 'duration_s': float(duration_s), 'success_rate': float(sum((1 for w in workflows if w.success)) / max(1, len(workflows))), 'green_rate': float(sum((1 for w in workflows if w.green_ok)) / max(1, len(workflows))), 'goodput_green_per_s': float(goodput), 'latency_ms': {'p50': _pct(lat, 50), 'p95': _pct(lat, 95), 'p99': _pct(lat, 99), 'mean': float(np.mean(lat)) if lat else float('nan')}}
    if energy:
        out['energy_j'] = {'p50': _pct([float(e) for e in energy], 50), 'p95': _pct([float(e) for e in energy], 95), 'p99': _pct([float(e) for e in energy], 99), 'mean': float(np.mean([float(e) for e in energy]))}
    else:
        out['energy_j'] = None
    tiers = sorted(set((w.sla_tier for w in workflows)))
    per_tier: Dict[str, Any] = {}
    for t in tiers:
        ws = [w for w in workflows if w.sla_tier == t]
        per_tier[t] = {'n': len(ws), 'green_rate': float(sum((1 for w in ws if w.green_ok)) / max(1, len(ws))), 'lat_p99': _pct([w.latency_ms for w in ws], 99)}
    out['per_tier'] = per_tier
    return out
