"""Qualify or run two frozen complete Linux comparison blocks sequentially."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

F = Path(__file__).resolve().parent
ROOT = F.parents[1]
REMOTE = Path('/home/jules/experiments/pvass-publication')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
now = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()


def write(path, value):
    with path.open('x') as out:
        json.dump(value, out, indent=2)
        out.write('\n')


def command(plan, block):
    absolute = lambda p: str(REMOTE / p)
    methods = block['methods']
    cmd = [absolute('vendor/venv/bin/python'), '-u',
           absolute(plan['runner_source'] + '/scripts/benchmark_smpt_classic.py'),
           '--workspace-root', str(REMOTE), '--corpus', absolute(plan['corpus']),
           '--binary', absolute(plan['candidate_binary']),
           '--native-tool', 'native-excess', 'portfolio-excess', absolute(plan['candidate_binary']),
           '--methods', *methods,
           '--buffer-agglomeration-method', 'native-excess',
           '--rust-original', '--smpt-original', '--bounded-validation',
           '--native-python', absolute('vendor/venv/bin/python'),
           '--validation-seconds', '60', '--validation-memory-mib', '2048',
           '--validation-response-mib', '64', '--validation-dag-work', '200000000',
           '--linux-cpus', '8', '--perf', '--memory-mib', '2048',
           '--max-states', '2000000', '--outer-grace', '0',
           '--smpt-root', absolute('vendor/SMPT-portable'),
           '--smpt-python', absolute('vendor/venv/bin/python'),
           '--tool-bin', absolute('vendor/tina-linux/tina-4.0.0/bin'),
           '--tool-bin', absolute('vendor/4ti2-install/bin'),
           '--tool-bin', absolute(plan['minizinc_tool_bin']),
           '--verifypn-binary', plan['verifypn']['binary'],
           '--verifypn-root', plan['verifypn']['source'],
           *plan['its_harness_options'],
           '--order-seed', str(block['order_seed']),
           '--output', absolute(block['output']), '--seconds', '5', '--repeat', '1']
    return cmd


def verify_pins(plan):
    for name, digest in plan['required_file_sha256'].items():
        assert sha(ROOT / name) == digest, name
    for name, digest in plan.get('external_file_sha256', {}).items():
        assert Path(name).is_absolute() and sha(Path(name)) == digest, name


def environment():
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    for key in list(env):
        if key.startswith('VASS_') and ('PROFILE' in key or 'DIAGNOSTIC' in key):
            env.pop(key)
    return env


def load():
    assert sys.platform == 'linux' and ROOT == REMOTE
    plan = json.loads((F / 'plan.json').read_text())
    assert plan['properties'] == 368 and plan['expected_rows'] == 2944
    assert plan['methods'] == ['native-excess', 'verifypn-default', 'smpt-mcc-portable', 'its-mcc']
    sys.path.insert(0, str(ROOT / plan['runner_source'] / 'scripts'))
    from process_runner import workspace_workloads
    assert not workspace_workloads(ROOT), 'Competing workspace workload'
    verify_pins(plan)
    subprocess.run([str(ROOT / 'vendor/venv/bin/python'), str(ROOT / plan['minizinc_preflight'])],
                   cwd=ROOT, env=environment(), check=True)
    return plan


def qualify():
    plan = load()
    import importlib.util
    spec = importlib.util.spec_from_file_location('capability', F / 'capability.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.run(plan, command)


def launch():
    plan = load()
    capability = json.loads((F / 'capability.json').read_text())
    assert capability['status'] == 'passed'
    assert capability['plan_sha256'] == sha(F / 'plan.json')
    assert capability['methods'] == plan['methods']
    assert not (F / 'execution.json').exists()
    for block in plan['blocks']:
        assert not (ROOT / block['output']).exists()
        assert not (F / (block['name'] + '-execution.json')).exists()
    from process_runner import workspace_workloads
    write(F / 'execution.json', dict(plan_sha256=sha(F / 'plan.json'),
          capability_sha256=sha(F / 'capability.json'), started_utc=now(), pid=os.getpid()))
    completed = []
    code = 1
    try:
        for block in plan['blocks']:
            assert not workspace_workloads(ROOT)
            verify_pins(plan)
            cmd = command(plan, block)
            assert cmd == block['command']
            write(F / (block['name'] + '-execution.json'),
                  dict(plan_sha256=sha(F / 'plan.json'), command=cmd, started_utc=now()))
            print(json.dumps(dict(event='block-start', block=block['name'])), flush=True)
            with (F / (block['name'] + '.log')).open('xb') as log:
                code = subprocess.run(cmd, cwd=ROOT, env=environment(),
                                      stdout=log, stderr=subprocess.STDOUT).returncode
            output = ROOT / block['output']
            pins = {str(p.relative_to(ROOT)): sha(p) for p in sorted(output.rglob('*')) if p.is_file()}
            rows = sum(1 for _ in (output / 'runs.jsonl').open()) if (output / 'runs.jsonl').exists() else 0
            write(F / (block['name'] + '-terminal.json'),
                  dict(plan_sha256=sha(F / 'plan.json'), exit_code=code, rows=rows,
                       artifact_sha256=pins, finished_utc=now()))
            if code or rows != 1472:
                code = code or 1
                break
            completed.append(block['name'])
            print(json.dumps(dict(event='block-complete', block=block['name'])), flush=True)
    finally:
        if len(completed) != len(plan['blocks']):
            code = code or 1
        write(F / 'terminal.json', dict(plan_sha256=sha(F / 'plan.json'), exit_code=code,
              completed=completed, finished_utc=now()))
    raise SystemExit(code)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['qualify', 'launch'])
    args = parser.parse_args()
    globals()[args.action]()
