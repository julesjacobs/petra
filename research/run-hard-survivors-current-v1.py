"""Print the registered command; --launch explicitly executes on an idle Linux host."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--launch', action='store_true')
    parser.add_argument('--terminal-predecessor')
    args = parser.parse_args()
    path = ROOT / 'research/hard-survivors-current-v1/plan.json'
    plan = json.loads(path.read_text())
    helper = ROOT / 'research/run-application-ladder-qualification-v1.py'
    assert hashlib.sha256(helper.read_bytes()).hexdigest() == plan['required_file_sha256'][str(helper.relative_to(ROOT))]
    spec = importlib.util.spec_from_file_location('qualification_command', helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    command = module.command(plan)
    print(shlex.join(command), flush=True)
    if args.launch:
        if not args.terminal_predecessor or sys.platform != 'linux' or ROOT != Path('/home/jules/experiments/pvass-publication'):
            parser.error('Launch needs registered Linux workspace and confirmed terminal predecessor identity')
        os.chdir(ROOT)
        sys.path.insert(0, str(ROOT / 'scripts'))
        from process_runner import workspace_workloads
        if workspace_workloads(ROOT) or (ROOT / plan['output']).exists():
            parser.error('Active workspace workload or existing output')
        for name, digest in plan['required_file_sha256'].items():
            with (ROOT / name).open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != digest:
                    parser.error('Identity mismatch: ' + name)
        environment = dict(os.environ)
        for key in ['VASS_RELAXED_PROFILE', 'VASS_PORTFOLIO_PROFILE', 'VASS_RAW_PHASE_DIAGNOSTICS', 'VASS_RAW_NEGATIVE_DIAGNOSTICS']:
            environment.pop(key, None)
        subprocess.run(['vendor/venv/bin/python', plan['minizinc_preflight']], env=environment, check=True)
        print(json.dumps(dict(plan_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                              terminal_predecessor=args.terminal_predecessor)), flush=True)
        sys.exit(subprocess.run(command, env=environment).returncode)
