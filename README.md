# QueueBreak: A Trace-to-Diagnosis Pipeline for Tail Latency in Agentic LLM Services

This repository contains the public source release for **QueueBreak**, a workflow-aware diagnostic framework for understanding tail latency in agentic LLM services.

QueueBreak answers a simple but operationally important question:

> When workflow p99 becomes large, is the tail dominated mainly by **waiting before execution** or by **execution itself**?

The repository includes the runnable evaluation pipeline, the agentic workflow simulator, experiment configurations, and the figure-generation script used for the paper.

## Overview

QueueBreak is built around a lightweight **trace-to-diagnosis (T2D)** pipeline that:

- reconstructs workflow boundaries from lightweight workflow and step traces,
- separates **waiting before execution** from **execution time**,
- summarizes tail behavior across operating conditions,
- identifies whether the tail is **queue dominated**, **execution dominated**, or **mixed**, and
- validates the diagnosis through intervention-based comparison.

The public package name remains `greenslo`.

## Repository Layout

```text
.
├── configs/
│   ├── exp_smoke.yaml
│   ├── exp_demo.yaml
│   ├── exp_suite_A_underload_mixed_relaxed.yaml
│   ├── exp_suite_B_midload_mixed_relaxed.yaml
│   ├── exp_suite_C_overload_mixed_relaxed.yaml
│   ├── exp_suite_D_underload_eco_only_relaxed.yaml
│   ├── exp_suite_E_midload_mixed_relaxed_fail02.yaml
│   ├── exp_suite_F_underload_fast_only_relaxed.yaml
│   ├── suite_paper_relaxed.yaml
│   ├── suite_paper_tight.yaml
│   ├── models.yaml
│   ├── slas.yaml
│   └── slas_relaxed.yaml
├── greenslo/
│   ├── agentic_workflows/
│   ├── agents/
│   ├── data/
│   ├── eval/
│   ├── mcp/
│   ├── measurement/
│   ├── orchestrator/
│   └── utils/
├── scripts/
│   └── queuebreak_make_figures.py
├── RUN_COMMANDS.md
├── README.md
└── requirements.txt
```

## What Is Included

- **Core package** under `greenslo/` for workflow generation, orchestration, tracing, metrics, and evaluation.
- **Runnable experiment configurations** under `configs/`.
- **Suite runner** for batch evaluation.
- **Standalone paper-figure generator** under `scripts/queuebreak_make_figures.py`.
- **Optional workload downloader** for JSONL prompt sources.

## What Is Not Included

This public release intentionally excludes generated artifacts and repository clutter. In particular, it does **not** include:

- prior `runs/` outputs,
- generated figures and PDFs,
- cached files and bytecode,
- bundled workload JSONL files,
- packaged artifact zips,
- logs, reports, and temporary outputs.

## Requirements

- Python **3.10+**
- `pip` for dependency installation
- Optional: NVIDIA GPU + NVML for energy measurement
- Optional: Hugging Face model downloads for non-mock execution
- Optional: Hugging Face `datasets` access for richer workload JSONL sources

All Python dependencies are listed in `requirements.txt`.

## Quick Start

### 1. Create a virtual environment and install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Optionally prepare workload JSONL files

This step is optional. If `data/workloads/` is missing, QueueBreak still runs using built-in fallback prompts.

```bash
python -m greenslo.data.download --out data/workloads --max_examples 200
```

### 3. Run the smoke test

```bash
python -m greenslo.eval.run \
  --config configs/exp_smoke.yaml \
  --workloads_dir data/workloads
```

Expected output directory:

```text
runs/smoke_<timestamp>/
```

### 4. Run the demo configuration

```bash
python -m greenslo.eval.run \
  --config configs/exp_demo.yaml \
  --workloads_dir data/workloads
```

Expected output directory:

```text
runs/demo_<timestamp>/
```

## Reproducing the Main Evaluation Suites

### Relaxed suite

```bash
python -m greenslo.eval.run_suite \
  --suite configs/suite_paper_relaxed.yaml \
  --workloads_dir data/workloads
```

### Tight suite

```bash
python -m greenslo.eval.run_suite \
  --suite configs/suite_paper_tight.yaml \
  --workloads_dir data/workloads
```

Each suite creates a timestamped directory containing:

- `suite_results.csv`
- `suite_report.md`
- `suite_logs/`
- individual experiment outputs under `runs/`

## Running Individual Experiments

### A. Underload, mixed workload

```bash
python -m greenslo.eval.run \
  --config configs/exp_suite_A_underload_mixed_relaxed.yaml \
  --workloads_dir data/workloads
```

### B. Midload, mixed workload

```bash
python -m greenslo.eval.run \
  --config configs/exp_suite_B_midload_mixed_relaxed.yaml \
  --workloads_dir data/workloads
```

### C. Overload, mixed workload

```bash
python -m greenslo.eval.run \
  --config configs/exp_suite_C_overload_mixed_relaxed.yaml \
  --workloads_dir data/workloads
```

### D. Underload, eco-only SLA tier

```bash
python -m greenslo.eval.run \
  --config configs/exp_suite_D_underload_eco_only_relaxed.yaml \
  --workloads_dir data/workloads
```

### E. Midload with dependency degradation (`failure_prob = 0.2`)

```bash
python -m greenslo.eval.run \
  --config configs/exp_suite_E_midload_mixed_relaxed_fail02.yaml \
  --workloads_dir data/workloads
```

### F. Underload, fast-only SLA tier

```bash
python -m greenslo.eval.run \
  --config configs/exp_suite_F_underload_fast_only_relaxed.yaml \
  --workloads_dir data/workloads
```

If you want the tight variants, replace `*_relaxed.yaml` with the corresponding `*_tight.yaml` file in `configs/`.

## Generating the Paper Figures

The repository includes a standalone figure generator for the paper plots.

```bash
python scripts/queuebreak_make_figures.py
```

Generated files are written to:

```text
generated_figures/
```

The script emits paper-style figure files including:

- `fig1_mixed_p99_decomp_log.pdf`
- `fig2_queue_dominance_signature.pdf`
- `fig4_fail_combined.pdf`
- `fig5_intervention_consistency.pdf`

PNG versions are also generated alongside the PDFs.

## Experiment-to-Paper Mapping

The repository covers the main experimental logic of the paper in two complementary ways:

1. **Runnable evaluation configs** under `configs/` exercise the full QueueBreak pipeline under representative operating conditions.
2. **Paper-ready figures** are generated by `scripts/queuebreak_make_figures.py`.

A useful mapping is:

- **Mixed-workload load sweep**: `A/B/C` configs + `fig1_mixed_p99_decomp_log` and `fig2_queue_dominance_signature`
- **Dependency degradation / tool failure**: `E` config + `fig4_fail_combined`
- **SLA-specific comparison settings**: `D` and `F` configs
- **Intervention consistency visualization**: `fig5_intervention_consistency`

## Typical Output Files

A single run directory usually contains some or all of the following files:

- `config_used.yaml`
- `summary.json`
- `workflows.jsonl`
- `steps.jsonl`
- `workflows.parquet` or `workflows.csv`
- `steps.parquet` or `steps.csv`
- `latency_cdf.png`
- `pareto_energy_latency.png`

A suite run additionally produces:

- `suite_results.csv`
- `suite_report.md`
- `suite_logs/*.stdout.log`
- `suite_logs/*.stderr.log`

## Reported Metrics

The runtime summary includes:

- `success_rate`
- `green_rate`
- `goodput_green_per_s`
- `latency_ms.p50`
- `latency_ms.p95`
- `latency_ms.p99`
- `latency_ms.mean`
- `energy_j.p50`
- `energy_j.p95`
- `energy_j.p99`
- `energy_j.mean`
- per-tier summary statistics under `per_tier`

## Notes on Models, GPU, and Fallback Behavior

- The default configs reference Qwen-family models in `configs/models.yaml`.
- If model loading fails, the runtime automatically falls back to a deterministic **MockLLM** path so the full pipeline still executes.
- The smoke test explicitly enables fallback models for quick verification.
- GPU power measurement is optional. If NVML is unavailable or no NVIDIA GPU is present, energy metrics may be `None`.
- Workload JSONL files are optional. If `data/workloads/` is absent, the workflow generator uses built-in fallback prompt sources.

## Minimal End-to-End Command Sequence

If you just want the shortest working path:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python -m greenslo.data.download --out data/workloads --max_examples 200
python -m greenslo.eval.run --config configs/exp_smoke.yaml --workloads_dir data/workloads
python -m greenslo.eval.run_suite --suite configs/suite_paper_relaxed.yaml --workloads_dir data/workloads
python scripts/queuebreak_make_figures.py
```

## Reproducibility Notes

- The evaluation runner seeds the global random state from each config.
- Arrival processes, workflow generation, and tool behavior are all config-driven.
- Public configs are intended to be runnable out of the box with optional fallback behavior when models, datasets, or GPU telemetry are unavailable.

## Citation

If you use this repository, please cite the QueueBreak paper:

```text
QueueBreak: A Trace-to-Diagnosis Pipeline for Tail Latency in Agentic LLM Services
```
