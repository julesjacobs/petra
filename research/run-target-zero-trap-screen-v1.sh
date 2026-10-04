#!/bin/sh
set -eu
cd /Users/julesjacobs/git/git/pvass
unset VASS_RELAXED_PROFILE VASS_PORTFOLIO_PROFILE
vendor/venv/bin/python - <<'PY'
import hashlib,json
from pathlib import Path
from scripts.process_runner import workspace_workloads
if workspace_workloads(Path.cwd()):
    raise RuntimeError('Local workload still active')
p=json.loads(Path('research/target-zero-trap-screen-v1-plan.json').read_text())
if Path(p['output']).exists():
    raise RuntimeError('Refusing existing output')
for name,expected in p['required_file_sha256'].items():
    with Path(name).open('rb') as stream:
        assert hashlib.file_digest(stream,'sha256').hexdigest()==expected,name
print('Frozen identities checked; starting104-query target-zero trap ablation.',flush=True)
PY
vendor/venv/bin/python -u scripts/benchmark_smpt_classic.py --corpus benchmarks/candidate-challenges-v1 --binary results/solver-target-zero-trap-v1/vass-reach --native-tool before portfolio-focused results/solver-target-zero-trap-v1/vass-reach --native-tool after portfolio-focused results/solver-target-zero-trap-v1/vass-reach --methods before after --target-zero-trap-method after --rust-original --bounded-validation --validation-seconds 60 --validation-memory-mib 2048 --validation-response-mib 64 --validation-dag-work 200000000 --track-resources --memory-mib 2048 --outer-grace 0 --max-states 2000000 --order-seed 20261101 --output results/target-zero-trap-screen-v1 --seconds 5 --repeat 1
