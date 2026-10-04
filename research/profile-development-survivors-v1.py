"""Stage diagnostics for all survivor branches; excluded from benchmark results."""
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from process_runner import run, workspace_workloads

F = ROOT / 'research/development-survivor-profiles-v1'
S = ROOT / 'results/solver-portfolio-reduced-development-v1/candidate'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
selection = ROOT / 'research/development-survivors-v1/plan.json'
inputs = json.loads(selection.read_text())['input_sha256']
assert not workspace_workloads(ROOT)
F.mkdir()
plan = dict(scope=__doc__, binary_sha256=sha(S), input_sha256=inputs,
            selection_sha256=sha(selection), script_sha256=sha(Path(__file__)),
            method='portfolio-reduced', internal_seconds=5, external_seconds=7,
            max_states=2000000, sampled_memory_bytes=2**31,
            environment={'VASS_PORTFOLIO_PROFILE': '1'})
(F / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n')
os.environ.update(plan['environment'])
for i, (path, digest) in enumerate(inputs.items()):
    assert sha(ROOT / path) == digest
    log = F / f'{i}.jsonl'
    cmd = [str(S), '--json', str(ROOT / path), '--method', plan['method'],
           '--seconds', '5', '--max-states', '2000000']
    wall, code, expired, resources = run(cmd, ROOT, 7, log, 2**31)
    row = dict(input=path, command=cmd, wall=wall, exit_code=code, expired=expired,
               resources=resources, log=log.name, log_sha256=sha(log))
    with (F / 'runs.jsonl').open('a') as out:
        out.write(json.dumps(row) + '\n')
    print(path, code, expired, flush=True)
(F / 'terminal.json').write_text(json.dumps(dict(exit_code=0, rows=len(inputs)))+'\n')
