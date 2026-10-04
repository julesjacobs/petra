#!/bin/sh
# Deploy and review first; run only with no other pvass measurement or build active.
set -eu
cd /home/jules/experiments/pvass-publication
vendor/venv/bin/python - <<'PY'
import hashlib
import json
from pathlib import Path

plan = json.loads(Path('research/application-gaps-v1-plan.json').read_text())
for name, expected in plan['required_file_sha256'].items():
    with Path(name).open('rb') as stream:
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    if actual != expected:
        raise SystemExit(f'Frozen file differs: {name}')
if Path(plan['output']).exists():
    raise SystemExit('Refusing an existing output directory')
print('Frozen inputs, runners and tools match the registered plan.', flush=True)
PY
vendor/venv/bin/python -u scripts/benchmark_smpt_classic.py \
  --corpus benchmarks/application-gaps-v1 \
  --binary results/linux-solver-capacity-direct-v1/vass-reach \
  --native-tool native-focused portfolio-focused results/linux-solver-capacity-direct-v1/vass-reach \
  --native-tool native-symbolic portfolio-symbolic results/linux-solver-capacity-direct-v1/vass-reach \
  --methods native-focused native-symbolic verifypn-default smpt-full-portable \
  --rust-original --smpt-original --bounded-validation \
  --validation-seconds 60 --validation-memory-mib 2048 \
  --validation-response-mib 64 --validation-dag-work 200000000 \
  --linux-cpus 8 --perf --memory-mib 2048 --max-states 2000000 --outer-grace 0 \
  --smpt-root vendor/SMPT-portable --smpt-python vendor/venv/bin/python \
  --tool-bin vendor/tina-linux/tina-4.0.0/bin --tool-bin vendor/4ti2-install/bin \
  --verifypn-binary vendor/verifypn/build-release/verifypn/bin/verifypn-linux64 \
  --order-seed 20261104 --output results/linux-application-gaps-v1 --seconds 60 --repeat 1
