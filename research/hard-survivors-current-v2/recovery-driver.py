"""Prepared recovery driver. Execution requires explicit Linux and plan-identity gates."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RECEIPTS = HERE / 'recovery-execution-v1'
PLAN = HERE / 'recovery-plan.json'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('w') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def now():
    return datetime.now(timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--plan-sha256')
    parser.add_argument('--record-service-terminal', action='store_true')
    args = parser.parse_args()
    if sys.platform != 'linux' or ROOT != Path('/home/jules/experiments/pvass-publication'):
        parser.error('Only the registered Linux workspace may execute this prepared driver')
    if args.record_service_terminal:
        write(RECEIPTS / ('service-terminal-' + os.environ['INVOCATION_ID'] + '.json'), dict(recorded_at=now(),
              service_result=os.environ.get('SERVICE_RESULT'), exit_code=os.environ.get('EXIT_CODE'),
              exit_status=os.environ.get('EXIT_STATUS'), invocation_id=os.environ.get('INVOCATION_ID'),
              boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
              scope='ExecStopPost receipt for top-level driver only. Verify benchmark units and workload absence before collecting or retrying; do not infer all cells completed.'))
        return 0
    if not args.execute or not args.plan_sha256 or sha(PLAN) != args.plan_sha256:
        parser.error('Explicit --execute and exact --plan-sha256 are required')
    if RECEIPTS.exists():
        parser.error('Refusing to reuse recovery receipts; inspect prior attempt')
    RECEIPTS.mkdir()
    state = dict(status='preflight', start=now(), plan_sha256=args.plan_sha256, cells=[],
                 boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip())
    code = 1
    def interrupted(signum, _frame):
        raise RuntimeError(f'Driver received signal {signum}; inspect sibling benchmark units')
    for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(signum, interrupted)
    try:
        plan = json.loads(PLAN.read_text())
        for relative, expected in plan['required_file_sha256'].items():
            if sha(ROOT / relative) != expected:
                raise RuntimeError('Registered byte mismatch: ' + relative)
        for cell in plan['cells']:
            if (ROOT / cell['output']).exists():
                raise RuntimeError('Refusing to overwrite output: ' + cell['output'])
        if subprocess.check_output(['loginctl', 'show-user', 'jules', '--property=Linger', '--value'], text=True).strip() != 'yes':
            raise RuntimeError('User manager lingering is required for disconnect survival')
        sys.path.insert(0, str(ROOT / 'scripts'))
        from process_runner import workspace_workloads
        def idle():
            if workspace_workloads(ROOT):
                raise RuntimeError('Workspace workloads present')
            units = subprocess.check_output(['systemctl', '--user', 'list-units', '--state=running',
                                             '--no-legend', '--plain', 'pvass-*.service'], text=True)
            if any(line.split()[0] != 'pvass-hard-survivors-recovery-v1.service' for line in units.splitlines() if line.strip()):
                raise RuntimeError('Other benchmark systemd units present')
        idle()
        environment = dict(os.environ)
        for key in ('VASS_PORTFOLIO_PROFILE', 'VASS_RELAXED_PROFILE', 'VASS_RAW_PHASE_DIAGNOSTICS', 'VASS_RAW_NEGATIVE_DIAGNOSTICS'):
            environment.pop(key, None)
        subprocess.run(['vendor/venv/bin/python', plan['minizinc_preflight']], cwd=ROOT,
                       env=environment, check=True)
        state['status'] = 'running'
        write(RECEIPTS / 'progress.json', state)
        for cell in plan['cells']:
            idle()
            state['active_cell'] = cell['sequence']
            write(RECEIPTS / 'progress.json', state)
            result = subprocess.run(cell['command'], cwd=ROOT, env=environment)
            record = dict(sequence=cell['sequence'], query=cell['query'], method=cell['method'],
                          repeat=cell['repeat'], output=cell['output'], driver_exit_code=result.returncode,
                          finished_at=now())
            output = ROOT / cell['output']
            run_path = output / 'runs.jsonl'
            rows = [json.loads(line) for line in run_path.read_text().splitlines()] if run_path.exists() else []
            if run_path.exists():
                record['runs_sha256'] = sha(run_path)
            record['recorded_rows'] = len(rows)
            state['cells'].append(record)
            write(RECEIPTS / 'progress.json', state)
            if result.returncode != 0 or len(rows) != 1 or any(rows[0].get(k) != cell[k] for k in ('query', 'method', 'repeat')):
                raise RuntimeError(f'Cell {cell["sequence"]} needs inspection; no automatic retry')
        idle()
        state.update(status='completed-awaiting-audit', active_cell=None)
        code = 0
    except BaseException as error:
        state.update(status='interrupted-or-failed', error=f'{type(error).__name__}: {error}')
    finally:
        state.update(finished_at=now(), driver_exit_code=code)
        write(RECEIPTS / 'driver-terminal.json', state)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
