#!/bin/sh
set -eu
cd /home/jules/experiments/pvass-publication
unset VASS_RELAXED_PROFILE VASS_PORTFOLIO_PROFILE
vendor/venv/bin/python - <<'PY'
import hashlib,json
from pathlib import Path
from scripts.process_runner import workspace_workloads
assert not workspace_workloads(Path.cwd())
plan=json.loads(Path('research/application-portfolio-comparison-v1-plan.json').read_text())
assert not Path(plan['output']).exists()
for name,expected in plan['required_file_sha256'].items():
    with Path(name).open('rb') as stream:
        assert hashlib.file_digest(stream,'sha256').hexdigest()==expected,name
print('All registered inputs, runtime sources and tools verified; starting656-slot comparison.',flush=True)
PY
vendor/venv/bin/python research/check-smpt-minizinc-repair-v1.py
vendor/venv/bin/python -u scripts/benchmark_smpt_classic.py \
  --corpus benchmarks/application-portfolio-comparison-v1 \
  --binary results/linux-solver-repeated-search-v1/vass-reach \
  --native-tool native-frozen portfolio-focused results/linux-solver-capacity-direct-v1/vass-reach \
  --native-tool native-buffer portfolio-focused results/linux-solver-repeated-search-v1/vass-reach \
  --native-tool native-batched portfolio-batched results/linux-solver-repeated-search-v1/vass-reach \
  --methods native-frozen native-buffer native-batched verifypn-default smpt-full-portable \
  --buffer-agglomeration-method native-buffer --buffer-agglomeration-method native-batched \
  --rust-original --smpt-original --bounded-validation \
  --validation-seconds 60 --validation-memory-mib 2048 \
  --validation-response-mib 64 --validation-dag-work 200000000 \
  --linux-cpus 8 --perf --memory-mib 2048 --max-states 2000000 --outer-grace 0 \
  --smpt-root vendor/SMPT-portable --smpt-python vendor/venv/bin/python \
  --tool-bin vendor/tina-linux/tina-4.0.0/bin --tool-bin vendor/4ti2-install/bin \
  --tool-bin vendor/minizinc-linux-v1/MiniZincIDE-2.10.1-x86_64-linux-gnu/bin \
  --verifypn-binary vendor/verifypn/build-release/verifypn/bin/verifypn-linux64 \
  --order-seed 20261109 --output results/linux-application-portfolio-comparison-v1 --seconds 5 --repeat 1
