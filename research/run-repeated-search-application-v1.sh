#!/bin/sh
set -eu
cd /Users/julesjacobs/git/git/pvass
unset VASS_RELAXED_PROFILE VASS_PORTFOLIO_PROFILE
vendor/venv/bin/python - <<'PY'
import hashlib,json
from pathlib import Path
from scripts.process_runner import workspace_workloads
assert not workspace_workloads(Path.cwd())
p=json.loads(Path('research/repeated-search-application-v1-plan.json').read_text())
assert not Path(p['output']).exists()
for name,expected in p['required_file_sha256'].items():
    with Path(name).open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==expected,name
print('Registered identities verified; starting full192-query repeated-firing comparison.',flush=True)
PY
vendor/venv/bin/python -u scripts/benchmark_smpt_classic.py --corpus benchmarks/application-expansion-v1 --binary results/solver-repeated-search-v1/vass-reach --native-tool control portfolio-focused results/solver-repeated-search-v1/vass-reach --native-tool batched portfolio-batched results/solver-repeated-search-v1/vass-reach --methods control batched --buffer-agglomeration-method control --buffer-agglomeration-method batched --rust-original --bounded-validation --validation-seconds 60 --validation-memory-mib 2048 --validation-response-mib 64 --validation-dag-work 200000000 --track-resources --memory-mib 2048 --outer-grace 0 --max-states 2000000 --order-seed 20261107 --output results/repeated-search-application-v1 --seconds 5 --repeat 1
