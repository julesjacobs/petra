"""Qualify or execute an immutable, sequential six-block Linux comparison."""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
F = ROOT/'research/repeated-comparison-linux-v1'
REMOTE = Path('/home/jules/experiments/pvass-publication')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
now = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()

def load(name):
    spec = importlib.util.spec_from_file_location(name.replace('-','_'),ROOT/'research'/f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def write(path,value):
    with path.open('x') as out:
        json.dump(value,out,indent=2)
        out.write('\n')

def plans():
    suite = json.loads((F/'suite.json').read_text())
    assert suite['rows']==4224 and len(suite['blocks'])==6
    result = []
    for block in suite['blocks']:
        folder = F/block['name']
        assert sha(folder/'plan.json')==block['plan_sha256']
        plan = json.loads((folder/'plan.json').read_text())
        assert plan['seconds']==block['seconds'] and plan['order_seed']==block['order_seed']
        assert list(plan['methods'])==suite['methods']
        result.append((folder,plan))
    return suite,result

def verify_pins(plan):
    for path,digest in {**plan['required_file_sha256'],**plan['preflight_file_sha256']}.items():
        assert sha(ROOT/path)==digest,path

def qualify():
    suite,blocks = plans()
    verify_pins(blocks[0][1])
    sources = {}
    for folder,plan in blocks:
        budget = plan['seconds']
        if budget not in sources:
            preflight = load('preflight-portfolio-reduced-linux-v1')
            preflight.FOLDER = folder
            preflight.CORPUS = ROOT/f'benchmarks/repeated-capability-{budget}s-v1'
            preflight.OUTPUT = ROOT/f'results/linux-repeated-capability-{budget}s-v1'
            preflight.main()
            components = load('preflight-portfolio-reduced-components-v1')
            components.FOLDER = folder
            components.main()
            sources[budget] = folder
        else:
            source = sources[budget]
            source_plan = json.loads((source/'plan.json').read_text())
            changes = {k for k in plan if plan[k]!=source_plan[k]}
            assert changes=={'output','order_seed','suite_block','capability_preflight'},changes
            receipt = json.loads((source/'capability.json').read_text())
            assert receipt['status']=='passed' and receipt['plan_sha256']==sha(source/'plan.json')
            receipt.update(plan_sha256=sha(folder/'plan.json'),derivation=dict(
                source=str((source/'capability.json').relative_to(ROOT)),source_sha256=sha(source/'capability.json'),
                source_plan_sha256=sha(source/'plan.json'),changed_fields=sorted(changes),
                reason='Only output locations and registered query-order seed differ; solver, budget, resources and runner are identical.'))
            write(folder/'capability.json',receipt)
    write(F/'qualification.json',dict(status='passed',suite_sha256=sha(F/'suite.json'),
          capability_sha256={folder.name:sha(folder/'capability.json') for folder,_ in blocks},
          fresh_budgets=sorted(sources),harness_rows=32,component_rows=10))

def launch():
    suite,blocks = plans()
    q = json.loads((F/'qualification.json').read_text())
    assert q['status']=='passed' and q['suite_sha256']==sha(F/'suite.json')
    for folder,plan in blocks:
        assert sha(folder/'capability.json')==q['capability_sha256'][folder.name]
        receipt = json.loads((folder/'capability.json').read_text())
        assert receipt['status']=='passed' and receipt['plan_sha256']==sha(folder/'plan.json')
        assert receipt['methods']==list(plan['methods']) and receipt['runner_archive_sha256']==plan['runner_archive_sha256']
        assert not (ROOT/plan['output']).exists() and not (folder/'execution.json').exists()
    verify_pins(blocks[0][1])
    sys.path.insert(0,str(ROOT/blocks[0][1]['runner_source']/'scripts'))
    from process_runner import workspace_workloads
    assert not workspace_workloads(ROOT)
    command = load('run-portfolio-reduced-linux-v1').command
    env = dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
    for key in list(env):
        if key.startswith('VASS_') and ('PROFILE' in key or 'DIAGNOSTIC' in key):
            env.pop(key)
    write(F/'execution.json',dict(suite_sha256=sha(F/'suite.json'),qualification_sha256=sha(F/'qualification.json'),started_utc=now(),pid=os.getpid()))
    completed = []
    code = 1
    try:
        for folder,plan in blocks:
            assert not workspace_workloads(ROOT)
            verify_pins(plan)
            subprocess.run([str(ROOT/'vendor/venv/bin/python'),str(ROOT/plan['minizinc_preflight'])],cwd=ROOT,env=env,check=True)
            cmd = command(plan)
            write(folder/'execution.json',dict(plan_sha256=sha(folder/'plan.json'),command=cmd,
                  capability_receipt=str(folder/'capability.json'),capability_receipt_sha256=sha(folder/'capability.json'),
                  started_utc=now(),pid=os.getpid()))
            print(json.dumps(dict(event='block-start',block=folder.name)),flush=True)
            with (folder/'run.log').open('xb') as log:
                code = subprocess.run(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT).returncode
            write(folder/'terminal.json',dict(plan_sha256=sha(folder/'plan.json'),exit_code=code,finished_utc=now()))
            if code!=0: break
            completed.append(folder.name)
            print(json.dumps(dict(event='block-complete',block=folder.name)),flush=True)
    finally:
        if len(completed)!=len(blocks): code = code or 1
        write(F/'terminal.json',dict(suite_sha256=sha(F/'suite.json'),exit_code=code,completed=completed,finished_utc=now()))
    raise SystemExit(code)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['qualify','launch'])
    args=parser.parse_args()
    assert sys.platform=='linux' and ROOT==REMOTE
    (qualify if args.action=='qualify' else launch)()
