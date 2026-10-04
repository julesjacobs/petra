"""Print registered commands; --launch explicitly runs one already-deployed stage."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REMOTE = Path('/home/jules/experiments/pvass-publication')


def command(plan):
    cmd = ['vendor/venv/bin/python', '-u', 'scripts/benchmark_smpt_classic.py',
           '--corpus', plan['corpus'], '--binary', plan['native_binary']]
    for label, tool in plan['native_tools'].items():
        cmd += ['--native-tool', label, tool['engine'], tool['binary']]
    cmd += ['--methods', *plan['methods']]
    for label in plan['buffer_agglomeration_methods']:
        cmd += ['--buffer-agglomeration-method', label]
    v = plan['validation']
    cmd += ['--rust-original', '--smpt-original', '--bounded-validation',
            '--validation-seconds', str(v['seconds']), '--validation-memory-mib', str(v['memory_mib']),
            '--validation-response-mib', str(v['response_mib']), '--validation-dag-work', str(v['dag_check_max_work']),
            '--linux-cpus', *map(str, plan['linux_cpus']), '--perf', '--memory-mib', str(plan['memory_mib']),
            '--max-states', str(plan['max_states']), '--outer-grace', str(plan['outer_grace']),
            '--smpt-root', 'vendor/SMPT-portable', '--smpt-python', 'vendor/venv/bin/python',
            '--tool-bin', 'vendor/tina-linux/tina-4.0.0/bin', '--tool-bin', 'vendor/4ti2-install/bin',
            '--tool-bin', plan['minizinc_tool_bin'], '--verifypn-binary', plan['verifypn']['binary'],
            '--order-seed', str(plan['order_seed']), '--output', plan['output'],
            '--seconds', str(plan['seconds']), '--repeat', str(plan['repeat'])]
    return cmd


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=int, choices=[60, 300], default=60)
    parser.add_argument('--launch', action='store_true')
    parser.add_argument('--terminal-predecessor', help='Recorded completed comparison/stage60 session identity; required for launch')
    args = parser.parse_args()
    path = ROOT / f'research/application-ladder-qualification-v1/plan-{args.stage}.json'
    plan = json.loads(path.read_text())
    if not plan['properties']:
        print('No joint survivors; no solver invocations registered.')
        sys.exit(0)
    cmd = command(plan)
    print(shlex.join(cmd), flush=True)
    if args.launch:
        if not args.terminal_predecessor or sys.platform != 'linux' or ROOT != REMOTE:
            parser.error('Launch requires the registered Linux workspace and a confirmed terminal predecessor session identity')
        os.chdir(ROOT)
        sys.path.insert(0, str(ROOT / 'scripts'))
        from process_runner import workspace_workloads
        if workspace_workloads(ROOT):
            parser.error('Workspace workload is active')
        if (ROOT / plan['output']).exists():
            parser.error('Registered output already exists')
        for name, expected in plan['required_file_sha256'].items():
            with (ROOT / name).open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
                    parser.error('Registered identity changed: ' + name)
        environment = dict(os.environ)
        for key in ('VASS_RELAXED_PROFILE', 'VASS_PORTFOLIO_PROFILE'):
            environment.pop(key, None)
        subprocess.run(['vendor/venv/bin/python', plan['minizinc_preflight']], check=True, env=environment)
        print(json.dumps(dict(plan_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                              terminal_predecessor=args.terminal_predecessor)), flush=True)
        sys.exit(subprocess.run(cmd, env=environment).returncode)
