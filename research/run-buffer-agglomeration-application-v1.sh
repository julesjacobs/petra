#!/bin/sh
set -eu
cd /Users/julesjacobs/git/git/pvass
unset VASS_RELAXED_PROFILE VASS_PORTFOLIO_PROFILE
vendor/venv/bin/python - <<'PY'
import hashlib,json
from pathlib import Path
from scripts.process_runner import workspace_workloads
assert not workspace_workloads(Path.cwd())
p=json.loads(Path('research/buffer-agglomeration-application-v1-plan.json').read_text())
assert not Path(p['output']).exists()
for name,expected in p['required_file_sha256'].items():
    with Path(name).open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==expected,name
print('Registered identities verified; starting full192-query buffer agglomeration comparison.',flush=True)
PY
vendor/venv/bin/python -u scripts/benchmark_smpt_classic.py --corpus benchmarks/application-expansion-v1 --binary results/solver-buffer-agglomeration-v2/vass-reach --native-tool control portfolio-focused results/solver-buffer-agglomeration-v2/vass-reach --native-tool buffer portfolio-focused results/solver-buffer-agglomeration-v2/vass-reach --methods control buffer --buffer-agglomeration-method buffer --rust-original --bounded-validation --validation-seconds 60 --validation-memory-mib 2048 --validation-response-mib 64 --validation-dag-work 200000000 --track-resources --memory-mib 2048 --outer-grace 0 --max-states 2000000 --order-seed 20261104 --output results/buffer-agglomeration-application-v1 --seconds 5 --repeat 1
