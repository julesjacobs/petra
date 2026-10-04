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
p=json.loads(Path('research/target-path-potential-screen-v1-plan.json').read_text())
if Path(p['output']).exists():
    raise RuntimeError('Refusing existing output')
for name,expected in p['required_file_sha256'].items():
    with Path(name).open('rb') as stream:
        assert hashlib.file_digest(stream,'sha256').hexdigest()==expected,name
print('Frozen identities checked; starting104-query four-configuration target-path potential ablation.',flush=True)
PY
vendor/venv/bin/python -u scripts/benchmark_smpt_classic.py --corpus benchmarks/candidate-challenges-v1 --binary results/solver-target-path-potential-v1/vass-reach --native-tool control portfolio-focused results/solver-target-path-potential-v1/vass-reach --native-tool trap portfolio-focused results/solver-target-path-potential-v1/vass-reach --native-tool potential portfolio-focused results/solver-target-path-potential-v1/vass-reach --native-tool combined portfolio-focused results/solver-target-path-potential-v1/vass-reach --methods control trap potential combined --target-zero-trap-method trap --target-zero-trap-method combined --target-path-potential-method potential --target-path-potential-method combined --rust-original --bounded-validation --validation-seconds 60 --validation-memory-mib 2048 --validation-response-mib 64 --validation-dag-work 200000000 --track-resources --memory-mib 2048 --outer-grace 0 --max-states 2000000 --order-seed 20261103 --output results/target-path-potential-screen-v1 --seconds 5 --repeat 1
