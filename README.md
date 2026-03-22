# QueueBreak Public Source Release

This repository contains the source code for the QueueBreak evaluation pipeline and the underlying agentic workflow simulator. The Python package name remains `greenslo`.

The public package keeps only reusable source code and runnable configuration files. Generated artifacts, logs, packaged outputs, cached files, bundled workload JSONL files, backup files, and pre-rendered figures have been removed.

## What is included

- `greenslo/`: core package for workflow generation, orchestration, tracing, metrics, and evaluation
- `configs/`: runnable experiment and suite configurations
- `scripts/queuebreak_make_figures.py`: standalone figure generator for the QueueBreak paper plots
- `requirements.txt`: Python dependencies
- `RUN_COMMANDS.md`: copy-paste run commands

## What is not included

- prior experiment outputs under `runs/`
- packaged artifact zip files
- cached bytecode and backup files
- bundled workload JSONL data
- generated reports, logs, PDFs, and PNGs

## Notes

- The code runs on CPU or GPU.
- If `transformers` or model weights are unavailable, the runtime falls back to deterministic mock generation so the pipeline still executes.
- GPU power measurement is optional. On machines without NVML or an NVIDIA GPU, energy values are recorded as `None` or `0` depending on the run path.
- Workload JSONL files are optional. If `data/workloads` is missing, the workflow generator falls back to built-in synthetic prompts.
