"""Print qualification command; launch only after deployment and capability checks."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REMOTE = Path('/home/jules/experiments/pvass-publication')
FOLDER = 'research/portfolio-reduced-linux-v1'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def command(plan):
    absolute = lambda value: str(REMOTE / value)
    result = [absolute('vendor/venv/bin/python'), '-u', absolute(plan['runner_source'] + '/scripts/benchmark_smpt_classic.py'),
              '--workspace-root', str(REMOTE), '--corpus', absolute(plan['corpus']),
              '--binary', absolute(plan['native_binary'])]
    for name, tool in plan['native_tools'].items():
        result += ['--native-tool', name, tool['engine'], tool['binary']]
    result += ['--methods', *plan['methods']]
    for name in plan['buffer_agglomeration_methods']:
        result += ['--buffer-agglomeration-method', name]
    check = plan['validation']
    result += ['--rust-original', '--smpt-original', '--bounded-validation',
        '--native-python', absolute('vendor/venv/bin/python'),
        '--validation-seconds', str(check['seconds']), '--validation-memory-mib', str(check['memory_mib']),
        '--validation-response-mib', str(check['response_mib']), '--validation-dag-work', str(check['dag_check_max_work']),
        '--linux-cpus', *map(str, plan['linux_cpus']), '--perf', '--memory-mib', str(plan['memory_mib']),
        '--max-states', str(plan['max_states']), '--outer-grace', str(plan['outer_grace']),
        '--smpt-root', absolute('vendor/SMPT-portable'), '--smpt-python', absolute('vendor/venv/bin/python'),
        '--tool-bin', absolute('vendor/tina-linux/tina-4.0.0/bin'), '--tool-bin', absolute('vendor/4ti2-install/bin'),
        '--tool-bin', absolute(plan['minizinc_tool_bin']), '--verifypn-binary', plan['verifypn']['binary'],
        '--verifypn-root', plan['verifypn']['source'], '--order-seed', str(plan['order_seed']),
        '--output', absolute(plan['output']), '--seconds', str(plan['seconds']), '--repeat', str(plan['repeat'])]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--launch', action='store_true')
    parser.add_argument('--capability-receipt', type=Path)
    args = parser.parse_args()
    plan_path = ROOT / FOLDER / 'plan.json'
    plan = json.loads(plan_path.read_text())
    cmd = command(plan)
    print(shlex.join(cmd), flush=True)
    if not args.launch:
        return
    if sys.platform != 'linux' or ROOT != REMOTE or args.capability_receipt is None:
        parser.error('Launch requires registered Linux root and a completed capability receipt')
    receipt = json.loads(args.capability_receipt.read_text())
    if not (receipt.get('status') == 'passed' and receipt.get('plan_sha256') == sha(plan_path)
            and receipt.get('runner_archive_sha256') == plan['runner_archive_sha256']
            and receipt.get('methods') == list(plan['methods'])):
        parser.error('Capability receipt must identify this plan, runner, and all six configurations')
    execution, terminal = ROOT / FOLDER / 'execution.json', ROOT / FOLDER / 'terminal.json'
    if any(p.exists() for p in (ROOT / plan['output'], execution, terminal)):
        parser.error('Existing output or execution receipt: no overwrite or implicit resume')
    sys.path.insert(0, str(ROOT / plan['runner_source'] / 'scripts'))
    from process_runner import workspace_workloads
    if workspace_workloads(ROOT):
        parser.error('Active common-workspace workload')
    link = ROOT / plan['runner_source'] / 'vendor'
    if not link.is_symlink() or link.resolve() != ROOT / 'vendor':
        parser.error('Isolated runner vendor symlink missing or wrong')
    for name, digest in {**plan['required_file_sha256'], **plan['preflight_file_sha256']}.items():
        if sha(ROOT / name) != digest:
            parser.error('Identity mismatch: ' + name)
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    for key in ('VASS_PORTFOLIO_PROFILE', 'VASS_RELAXED_PROFILE', 'VASS_RAW_PHASE_DIAGNOSTICS', 'VASS_RAW_NEGATIVE_DIAGNOSTICS'):
        environment.pop(key, None)
    subprocess.run([str(ROOT / 'vendor/venv/bin/python'), str(ROOT / plan['minizinc_preflight'])],
                   cwd=ROOT, env=environment, check=True)
    if workspace_workloads(ROOT):
        parser.error('Active common-workspace workload after preflight')
    with execution.open('x') as stream:
        json.dump(dict(plan_sha256=sha(plan_path), command=cmd, capability_receipt=str(args.capability_receipt),
                       capability_receipt_sha256=sha(args.capability_receipt), started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                       pid=os.getpid()), stream, indent=2)
    process = subprocess.Popen(cmd, cwd=ROOT, env=environment)
    code = process.wait()
    with terminal.open('x') as stream:
        json.dump(dict(plan_sha256=sha(plan_path), exit_code=code,
                       finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()), stream, indent=2)
    raise SystemExit(code)


if __name__ == '__main__':
    main()
