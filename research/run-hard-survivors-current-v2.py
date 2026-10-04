"""Print the registered full-cohort command; --launch explicitly runs on Linux."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def command(plan):
    result = ['vendor/venv/bin/python', '-u', 'scripts/benchmark_smpt_classic.py',
              '--corpus', plan['corpus'], '--binary', plan['native_binary']]
    for name in ['native-walk', 'native-batched', 'native-frozen']:
        tool = plan['native_tools'][name]
        result += ['--native-tool', name, tool['engine'], tool['binary']]
    result += ['--methods', *plan['methods']]
    for name in plan['buffer_agglomeration_methods']:
        result += ['--buffer-agglomeration-method', name]
    check = plan['validation']
    result += ['--rust-original', '--smpt-original', '--bounded-validation',
               '--validation-seconds', str(check['seconds']), '--validation-memory-mib', str(check['memory_mib']),
               '--validation-response-mib', str(check['response_mib']), '--validation-dag-work', str(check['dag_check_max_work']),
               '--linux-cpus', *map(str, plan['linux_cpus']), '--perf', '--memory-mib', str(plan['memory_mib']),
               '--max-states', str(plan['max_states']), '--outer-grace', str(plan['outer_grace']),
               '--smpt-root', 'vendor/SMPT-portable', '--smpt-python', 'vendor/venv/bin/python',
               '--tool-bin', 'vendor/tina-linux/tina-4.0.0/bin', '--tool-bin', 'vendor/4ti2-install/bin',
               '--tool-bin', plan['minizinc_tool_bin'], '--verifypn-binary', plan['verifypn']['binary'],
               '--order-seed', str(plan['order_seed']), '--output', plan['output'],
               '--seconds', str(plan['seconds']), '--repeat', str(plan['repeat'])]
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--launch', action='store_true')
    parser.add_argument('--terminal-predecessor', help='Operator-confirmed terminal session identity')
    args = parser.parse_args()
    path = ROOT / 'research/hard-survivors-current-v2/plan.json'
    plan = json.loads(path.read_text())
    cmd = command(plan)
    print(shlex.join(cmd), flush=True)
    if args.launch:
        if sys.platform != 'linux' or ROOT != Path('/home/jules/experiments/pvass-publication') or not args.terminal_predecessor:
            parser.error('Launch requires registered Linux workspace and confirmed terminal predecessor')
        os.chdir(ROOT)
        sys.path.insert(0, str(ROOT / 'scripts'))
        from process_runner import workspace_workloads
        if workspace_workloads(ROOT) or (ROOT / plan['output']).exists():
            parser.error('Active workspace workload or existing output')
        for name, expected in plan['required_file_sha256'].items():
            with (ROOT / name).open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
                    parser.error('Registered identity mismatch: ' + name)
        environment = dict(os.environ)
        for key in ['VASS_PORTFOLIO_PROFILE', 'VASS_RELAXED_PROFILE', 'VASS_RAW_PHASE_DIAGNOSTICS', 'VASS_RAW_NEGATIVE_DIAGNOSTICS']:
            environment.pop(key, None)
        subprocess.run(['vendor/venv/bin/python', plan['minizinc_preflight']], check=True, env=environment)
        print(json.dumps(dict(plan_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                              terminal_predecessor=args.terminal_predecessor)), flush=True)
        sys.exit(subprocess.run(cmd, env=environment).returncode)
