"""Record learned frontier constraints on all survivors; no benchmark verdicts."""
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from process_runner import run, workspace_workloads
F = ROOT/'research/frontier-sequences-v1'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert not workspace_workloads(ROOT)
F.mkdir()
shutil.copy2(ROOT/'target/release/vass-reach',F/'candidate')
paths = list((ROOT/'src').glob('*.rs'))+[Path(__file__),ROOT/'Cargo.toml',ROOT/'Cargo.lock']
for path in paths:
    dest = F/'source'/path.relative_to(ROOT)
    dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(path,dest)
inputs = json.loads((ROOT/'research/development-survivors-v1/plan.json').read_text())['input_sha256']
plan = dict(scope=__doc__, inputs=inputs, binary_sha256=sha(F/'candidate'),
            source_sha256={str(p.relative_to(ROOT)):sha(p) for p in paths},
            environment={'VASS_FRONTIER_PROFILE':'1'},internal_seconds=5,external_seconds=7,
            max_states=2000000,sampled_memory_bytes=2**31,rows=5)
(F/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
os.environ.update(plan['environment'])
for i,(path,digest) in enumerate(inputs.items()):
    assert sha(ROOT/path)==digest
    log = F/f'{i}.jsonl'
    cmd = [str(F/'candidate'),'--json',str(ROOT/path),'--method','frontier-count-plan',
           '--seconds','5','--max-states','2000000']
    wall,code,expired,res=run(cmd,ROOT,7,log,2**31)
    row=dict(input=path,command=cmd,wall=wall,exit_code=code,expired=expired,
             resources=res,log=log.name,log_sha256=sha(log))
    with (F/'runs.jsonl').open('a') as out:out.write(json.dumps(row)+'\n')
    print(path,code,expired,flush=True)
(F/'terminal.json').write_text(json.dumps(dict(exit_code=0,rows=5))+'\n')
