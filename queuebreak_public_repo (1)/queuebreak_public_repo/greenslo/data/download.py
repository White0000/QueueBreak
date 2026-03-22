from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any, Dict, List
from rich.console import Console
console = Console()

def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def _write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    with path.open('w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

def _fallback_ag_news(n: int) -> List[Dict[str, Any]]:
    return [{'text': 'World leaders meet to discuss climate policy and energy transition.', 'label': 0}, {'text': 'Tech company announces new GPU product for AI inference services.', 'label': 1}, {'text': 'Stock markets fluctuate amid economic uncertainty.', 'label': 2}, {'text': 'Local team wins championship after intense final match.', 'label': 3}] * max(1, n // 4)

def _fallback_samsum(n: int) -> List[Dict[str, Any]]:
    return [{'dialogue': 'A: The sensor is spiking again. B: Should we alert ops? A: Check anomaly first.', 'summary': 'They discuss checking anomaly before alerting.'}, {'dialogue': 'A: Device D1 seems offline. B: Try reading status and reboot if needed.', 'summary': 'They plan to check status and reboot.'}] * max(1, n // 2)

def _fallback_mbpp(n: int) -> List[Dict[str, Any]]:
    return [{'text': 'Write a function that returns the max of a list.', 'code': 'def f(xs): return max(xs)'}, {'text': 'Write a function that sums numbers from 1 to n.', 'code': 'def f(n): return n*(n+1)//2'}] * max(1, n // 2)

def _write_fallback(kind: str, out_path: Path, max_examples: int) -> None:
    if kind == 'ag_news':
        rows = _fallback_ag_news(max_examples)
    elif kind == 'samsum':
        rows = _fallback_samsum(max_examples)
    elif kind == 'mbpp':
        rows = _fallback_mbpp(max_examples)
    else:
        rows = [{'text': 'fallback'}]
    _write_jsonl(out_path, rows[:max_examples])
    console.print(f'[green]Wrote fallback[/green] -> {out_path} ({min(max_examples, len(rows))} rows)')

def _try_download(dataset_name: str, split: str, out_path: Path, max_examples: int, kind: str) -> None:
    try:
        from datasets import load_dataset
    except Exception as e:
        console.print(f'[yellow]datasets not available -> fallback for {dataset_name}. Error: {e}[/yellow]')
        _write_fallback(kind, out_path, max_examples)
        return
    try:
        ds = load_dataset(dataset_name, split=split)
        rows: List[Dict[str, Any]] = []
        for i, ex in enumerate(ds):
            if i >= max_examples:
                break
            if kind == 'ag_news':
                rows.append({'text': str(ex.get('text', '')), 'label': int(ex.get('label', 0))})
            elif kind == 'samsum':
                rows.append({'dialogue': str(ex.get('dialogue', '')), 'summary': str(ex.get('summary', ''))})
            elif kind == 'mbpp':
                rows.append({'text': str(ex.get('text', '')), 'code': str(ex.get('code', ''))})
            else:
                rows.append(dict(ex))
        if not rows:
            raise RuntimeError('empty_dataset')
        _write_jsonl(out_path, rows)
        console.print(f'[green]Downloaded[/green] {dataset_name}:{split} -> {out_path} ({len(rows)} rows)')
    except Exception as e:
        console.print(f'[yellow]Failed to download {dataset_name}:{split} -> fallback. Error: {e}[/yellow]')
        _write_fallback(kind, out_path, max_examples)

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='data/workloads', help='Output directory for JSONL files')
    ap.add_argument('--max_examples', type=int, default=200)
    args = ap.parse_args()
    out_dir = Path(args.out)
    _ensure_dir(out_dir)
    _try_download('ag_news', 'train', out_dir / 'ag_news.jsonl', args.max_examples, kind='ag_news')
    _try_download('samsum', 'train', out_dir / 'samsum.jsonl', args.max_examples, kind='samsum')
    _try_download('mbpp', 'train', out_dir / 'mbpp.jsonl', args.max_examples, kind='mbpp')
if __name__ == '__main__':
    main()
