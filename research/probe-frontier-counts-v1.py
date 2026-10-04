"""Matched branch-level diagnostic on every survivor; excluded from full benchmark tables."""
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from process_runner import run, workspace_workloads

F = ROOT / 'research/frontier-counts-v1'
OLD = ROOT / 'results/solver-portfolio-reduced-development-v1'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert not workspace_workloads(ROOT)
F.mkdir()
shutil.copy2(ROOT / 'target/release/vass-reach', F / 'candidate')
shutil.copy2(OLD / 'candidate', F / 'baseline')
assert sha(F / 'baseline') == json.loads((ROOT / 'research/portfolio-reduced-development-v1/plan.json').read_text())['native']['candidate']['binary_sha256']
paths = list((ROOT / 'src').glob('*.rs')) + list((ROOT / 'scripts').glob('*.py'))
paths += [ROOT / 'Cargo.toml', ROOT / 'Cargo.lock', Path(__file__)]
for p in paths:
    dest = F / 'source' / p.relative_to(ROOT)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(p, dest)
inputs = json.loads((ROOT / 'research/development-survivors-v1/plan.json').read_text())['input_sha256']
modes = {'candidate': 'frontier-count-plan', 'baseline': 'sparse-count-plan-budget'}
plan = dict(scope=__doc__, input_sha256=inputs, modes=modes, seconds=5, rows=10,
            max_states=2000000, sampled_memory_bytes=2**31, checker_seconds=30,
            binary_sha256={m: sha(F/m) for m in modes},
            source_sha256={str(p.relative_to(ROOT)): sha(p) for p in paths},
            checker= str(OLD / 'source/scripts/check_backend_answer.py'),
            checker_sha256=sha(OLD / 'source/scripts/check_backend_answer.py'))
(F / 'plan.json').write_text(json.dumps(plan, indent=2)+'\n')
for i, (path,digest) in enumerate(inputs.items()):
    assert sha(ROOT / path) == digest
    for mode in list(modes)[i%2:] + list(modes)[:i%2]:
        prefix = F / f'{i}.{mode}'
        log = Path(str(prefix)+'.json')
        cmd = [str(F/mode), '--json', str(ROOT/path), '--method', modes[mode],
               '--seconds', '5', '--max-states', '2000000']
        wall,code,expired,res = run(cmd, ROOT, 5, log, 2**31)
        try: answer = json.loads(log.read_text())
        except ValueError: answer = {}
        row = dict(input=path, mode=mode, command=cmd, wall=wall, exit_code=code,
                   expired=expired, resources=res, log=log.name, log_sha256=sha(log),
                   candidate_verdict=answer.get('verdict'), reason=answer.get('reason'),
                   states=answer.get('states'), verdict='unknown')
        if code == 0 and not expired and wall <= 5 and not res['memory_limit_exceeded'] and answer.get('verdict') in ['reachable','unreachable']:
            check = Path(str(prefix)+'.check.json')
            command = [sys.executable,plan['checker'],str(ROOT/path),str(log)]
            cw,cc,ce,cr = run(command,ROOT,30,check,2**31)
            row['check'] = dict(command=command,wall=cw,exit_code=cc,expired=ce,resources=cr,
                                log_sha256=sha(check),log=check.name)
            assert cc == 0 and not ce and cw <= 30 and not cr['memory_limit_exceeded']
            assert json.loads(check.read_text())['status'] == 'passed'
            row['verdict'] = answer['verdict']
        with (F / 'runs.jsonl').open('a') as out: out.write(json.dumps(row)+'\n')
        print(path,mode,row['verdict'],row['reason'],flush=True)
(F / 'terminal.json').write_text(json.dumps(dict(exit_code=0,rows=10))+'\n')
