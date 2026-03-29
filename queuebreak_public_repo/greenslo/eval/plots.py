from __future__ import annotations
from pathlib import Path
from typing import List
import matplotlib.pyplot as plt
from greenslo.measurement.trace import WorkflowRecord

def plot_pareto(workflows: List[WorkflowRecord], out_path: Path) -> None:
    xs = [w.energy_j for w in workflows if w.energy_j is not None]
    ys = [w.latency_ms for w in workflows if w.energy_j is not None]
    if not xs or not ys:
        return
    plt.figure()
    plt.scatter(xs, ys, s=12, alpha=0.7)
    plt.xlabel('Energy per workflow (J)')
    plt.ylabel('End-to-end latency (ms)')
    plt.title('Green-SLO Trade-off (energy vs latency)')
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()

def plot_latency_cdf(workflows: List[WorkflowRecord], out_path: Path) -> None:
    lat = sorted([w.latency_ms for w in workflows])
    if not lat:
        return
    n = len(lat)
    ys = [(i + 1) / n for i in range(n)]
    plt.figure()
    plt.plot(lat, ys)
    plt.xlabel('Latency (ms)')
    plt.ylabel('CDF')
    plt.title('Latency CDF')
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()
