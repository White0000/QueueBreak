Run Commands
1. Create a virtual environment
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
2. Optional: download or generate workload JSONL files
This step is optional. The simulator can run without data/workloads, but this command creates richer prompt sources.

python -m greenslo.data.download --out data/workloads --max_examples 200
3. Smoke test
python -m greenslo.eval.run --config configs/exp_smoke.yaml --workloads_dir data/workloads
Artifacts are written under runs/smoke_<timestamp>/.

4. Demo run
python -m greenslo.eval.run --config configs/exp_demo.yaml --workloads_dir data/workloads
Artifacts are written under runs/demo_<timestamp>/.

5. Tight suite
python -m greenslo.eval.run_suite --suite configs/suite_paper_tight.yaml --workloads_dir data/workloads
Artifacts are written under runs/suite_paper_tight_<timestamp>/.

6. Relaxed suite
python -m greenslo.eval.run_suite --suite configs/suite_paper_relaxed.yaml --workloads_dir data/workloads
Artifacts are written under runs/suite_paper_relaxed_<timestamp>/.

7. Useful variations
Run without pre-downloaded workloads:

python -m greenslo.eval.run --config configs/exp_smoke.yaml --workloads_dir data/workloads
Use the suite runner on a single config by editing the YAML in configs/ and re-running the matching command.

8. Typical output files
A run directory usually contains:

config_used.yaml
summary.json
workflows.jsonl
steps.jsonl
workflows.parquet or workflows.csv
steps.parquet or steps.csv
latency_cdf.png
pareto_energy_latency.png
