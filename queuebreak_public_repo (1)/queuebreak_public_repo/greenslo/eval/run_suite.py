from __future__ import annotations
import argparse
import csv
import datetime as _dt
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
try:
    import yaml
except Exception as e:
    raise SystemExit('PyYAML is required. Install with: pip install pyyaml') from e
_ARTIFACT_RE = re.compile('Artifacts written to:\\s*(.+)\\s*$', re.MULTILINE)

@dataclass
class ExpResult:
    exp_id: str
    module: str
    config: str
    run_dir: str
    status: str
    returncode: int
    n: Optional[int] = None
    duration_s: Optional[float] = None
    success_rate: Optional[float] = None
    green_rate: Optional[float] = None
    goodput_green_per_s: Optional[float] = None
    lat_p50_ms: Optional[float] = None
    lat_p95_ms: Optional[float] = None
    lat_p99_ms: Optional[float] = None
    lat_mean_ms: Optional[float] = None
    energy_p50_j: Optional[float] = None
    energy_p95_j: Optional[float] = None
    energy_p99_j: Optional[float] = None
    energy_mean_j: Optional[float] = None

def _now_tag() -> str:
    return _dt.datetime.now().strftime('%Y%m%d_%H%M%S')

def _parse_run_dir(text: str) -> Optional[str]:
    m = _ARTIFACT_RE.search(text or '')
    return m.group(1).strip().strip('"').strip("'") if m else None

def _safe_float(x: Any) -> Optional[float]:
    try:
        return None if x is None else float(x)
    except Exception:
        return None

def _safe_int(x: Any) -> Optional[int]:
    try:
        return None if x is None else int(x)
    except Exception:
        return None

def _read_summary(run_dir: Path) -> Dict[str, Any]:
    p = run_dir / 'summary.json'
    if not p.exists():
        raise FileNotFoundError(f'summary.json not found in {run_dir}')
    return json.loads(p.read_text(encoding='utf-8'))

def _extract_metrics(summary: Dict[str, Any]) -> Dict[str, Any]:
    lat = summary.get('latency_ms', {}) or {}
    en = summary.get('energy_j', {}) or {}
    return dict(n=_safe_int(summary.get('n')), duration_s=_safe_float(summary.get('duration_s')), success_rate=_safe_float(summary.get('success_rate')), green_rate=_safe_float(summary.get('green_rate')), goodput_green_per_s=_safe_float(summary.get('goodput_green_per_s')), lat_p50_ms=_safe_float(lat.get('p50')), lat_p95_ms=_safe_float(lat.get('p95')), lat_p99_ms=_safe_float(lat.get('p99')), lat_mean_ms=_safe_float(lat.get('mean')), energy_p50_j=_safe_float(en.get('p50')), energy_p95_j=_safe_float(en.get('p95')), energy_p99_j=_safe_float(en.get('p99')), energy_mean_j=_safe_float(en.get('mean')))

def _run_one(exp: Dict[str, Any], workloads_dir: str, cwd: Path, logs_dir: Path) -> ExpResult:
    exp_id = str(exp.get('id') or exp.get('name') or Path(str(exp.get('config', 'exp'))).stem)
    module = str(exp.get('module', 'greenslo.eval.run'))
    config = str(exp.get('config'))
    cmd = [sys.executable, '-m', module, '--config', config, '--workloads_dir', workloads_dir]
    if exp.get('extra_args'):
        cmd.extend([str(x) for x in exp['extra_args']])
    print(f'\n== Running {exp_id} ==')
    print('CMD:', ' '.join(cmd))
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, encoding='utf-8', errors='replace')
    (logs_dir / f'{exp_id}.stdout.log').write_text(proc.stdout or '', encoding='utf-8')
    (logs_dir / f'{exp_id}.stderr.log').write_text(proc.stderr or '', encoding='utf-8')
    combined = (proc.stdout or '') + '\n' + (proc.stderr or '')
    run_dir_s = _parse_run_dir(combined)
    run_dir = (cwd / run_dir_s).resolve() if run_dir_s else None
    if proc.returncode != 0 or run_dir is None or (not run_dir.exists()):
        return ExpResult(exp_id, module, config, str(run_dir) if run_dir else '', 'FAIL', proc.returncode)
    try:
        summary = _read_summary(run_dir)
        m = _extract_metrics(summary)
        return ExpResult(exp_id, module, config, str(run_dir), 'OK', proc.returncode, **m)
    except Exception:
        return ExpResult(exp_id, module, config, str(run_dir), 'FAIL', proc.returncode)

def _write_csv(path: Path, rows: List[ExpResult]) -> None:
    fieldnames = list(ExpResult.__dataclass_fields__.keys())
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r.__dict__)

def _fmt(x: Any) -> str:
    if x is None:
        return '-'
    if isinstance(x, float):
        if 0.0 <= x <= 1.0:
            return f'{x:.3f}'
        return f'{x:.1f}'
    return str(x)

def _write_md(path: Path, rows: List[ExpResult], suite_name: str) -> None:
    lines = []
    lines.append(f'# GreenSLO Suite Report: {suite_name}\n')
    lines.append(f"Generated: {_dt.datetime.now().isoformat(timespec='seconds')}\n")
    header = ['exp_id', 'status', 'green_rate', 'success_rate', 'lat_p99_ms', 'lat_p50_ms', 'energy_mean_j', 'run_dir', 'config']
    lines.append('| ' + ' | '.join(header) + ' |')
    lines.append('|' + '|'.join(['---'] * len(header)) + '|')
    for r in rows:
        lines.append('| ' + ' | '.join([r.exp_id, r.status, _fmt(r.green_rate), _fmt(r.success_rate), _fmt(r.lat_p99_ms), _fmt(r.lat_p50_ms), _fmt(r.energy_mean_j), r.run_dir.replace('\\', '/'), r.config.replace('\\', '/')]) + ' |')
    lines.append('\n## Logs\n\nEach experiment writes stdout/stderr logs under `suite_logs/`.\n')
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--suite', required=True)
    ap.add_argument('--workloads_dir', default=None)
    args = ap.parse_args()
    suite_path = Path(args.suite)
    suite = yaml.safe_load(suite_path.read_text(encoding='utf-8')) or {}
    suite_name = str(suite.get('suite_name') or suite_path.stem)
    workloads_dir = str(args.workloads_dir or suite.get('workloads_dir') or 'data/workloads')
    out_dir = Path(str(suite.get('out_dir') or 'runs'))
    experiments = suite.get('experiments') or []
    if not experiments:
        raise SystemExit('Suite has no experiments')
    suite_out = out_dir / f'suite_{suite_name}_{_now_tag()}'
    suite_out.mkdir(parents=True, exist_ok=True)
    logs_dir = suite_out / 'suite_logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    cwd = Path.cwd()
    results = []
    for exp in experiments:
        results.append(_run_one(exp, workloads_dir, cwd, logs_dir))
    _write_csv(suite_out / 'suite_results.csv', results)
    _write_md(suite_out / 'suite_report.md', results, suite_name)
    print('\n== Suite complete ==')
    print('Suite dir:', suite_out)
    print('CSV :', suite_out / 'suite_results.csv')
    print('MD  :', suite_out / 'suite_report.md')
if __name__ == '__main__':
    main()
