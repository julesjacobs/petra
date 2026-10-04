"""Explicitly launch the prepared, outcome-selected work-cap diagnostic once."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'research/signed-threshold-workcap-v1-plan.json'
PREFIX = ROOT / 'research/signed-threshold-workcap-v1'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_new(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def idle():
    sys.path.insert(0, str(ROOT / 'results/runner-threshold-v1/source/scripts'))
    from process_runner import workspace_workloads
    import psutil
    conflicts = workspace_workloads(ROOT)
    patterns = ('benchmark_', 'collect_stress_mcc.py', 'collect-', 'smpt_import.py',
                'native_original.py', 'rust_original_validation.py', 'bounded_validation.py')
    for process in psutil.process_iter(['pid', 'cmdline', 'cwd', 'status']):
        try:
            if process.pid == os.getpid() or process.info['status'] == psutil.STATUS_ZOMBIE:
                continue
            argv = process.info['cmdline'] or []
            if not any(any(pattern in Path(arg).name for pattern in patterns) for arg in argv[:3]):
                continue
            cwd = Path(process.info['cwd'] or '/').resolve()
            if cwd.is_relative_to(ROOT) or any(str(ROOT) in arg for arg in argv[:3]):
                conflicts.append(dict(pid=process.pid, command=argv[:3]))
        except (psutil.Error, OSError):
            continue
    if conflicts:
        raise RuntimeError(f'Conflicting local workloads; do not launch: {conflicts}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--launch', action='store_true', help='Required to start the diagnostic')
    args = parser.parse_args()
    if not args.launch:
        parser.error('Preparation does not execute solvers. Pass --launch explicitly when idle.')
    plan = json.loads(PLAN.read_text())
    output = Path(plan['command'][plan['command'].index('--output') + 1])
    execution = Path(str(PREFIX) + '-execution.json')
    terminal = Path(str(PREFIX) + '-terminal.json')
    log = Path(str(PREFIX) + '.log')
    if any(p.exists() for p in (output, execution, terminal, log)):
        raise FileExistsError('Diagnostic artifacts already exist; refuse to overwrite or resume')
    idle()
    for name, digest in plan['file_sha256'].items():
        if sha(ROOT / name) != digest:
            raise ValueError(f'Pinned artifact changed: {name}')
    idle()
    output.mkdir()
    write_new(execution, dict(plan_sha256=sha(PLAN), command=plan['command'],
        started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), launcher_pid=os.getpid(),
        selection_status=plan['selection_status'], parent_denominators=plan['parent_denominators']))
    with log.open('x') as stream:
        child = subprocess.Popen(plan['command'], cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                                 env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        code = child.wait()
    write_new(terminal, dict(exit_code=code, plan_sha256=sha(PLAN),
        finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    raise SystemExit(code)


if __name__ == '__main__':
    main()
