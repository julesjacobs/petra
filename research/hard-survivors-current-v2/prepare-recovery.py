"""Prepare missing-cell commands and service recipe locally; never execute them."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shlex

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
REMOTE = '/home/jules/experiments/pvass-publication'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    report = json.loads((HERE / 'interrupted-audit.json').read_text())
    original = json.loads((HERE / 'plan.json').read_text())
    assert report['status'] == 'incomplete' and report['available_row_audit'] == 'passed'
    assert len(report['missing_cells']) == 13
    helper = ROOT / 'research/run-hard-survivors-current-v2.py'
    spec = importlib.util.spec_from_file_location('original_launch_command', helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cells = []
    for cell in report['missing_cells']:
        selected = dict(original)
        selected['methods'] = {cell['method']: original['methods'][cell['method']]}
        selected['buffer_agglomeration_methods'] = [m for m in original['buffer_agglomeration_methods'] if m == cell['method']]
        selected['output'] = f'results/linux-hard-survivors-recovery-v1/cell-{cell["sequence"]:02}'
        command = module.command(selected) + ['--filter', '^' + re.escape(cell['query']) + '$']
        cells.append(dict(cell, output=selected['output'], command=command))
    required = dict(original['required_file_sha256'])
    for relative in (original['corpus'] + '/manifest.json', 'research/hard-survivors-current-v2/plan.json',
                     original['output'] + '/runs.jsonl', original['output'] + '/environment.json',
                     'research/hard-survivors-current-v2/recovery-driver.py',
                     'research/hard-survivors-current-v2/interrupted-audit.json',
                     original['minizinc_preflight']):
        required[relative] = sha(ROOT / relative)
    recovery = dict(status='prepared-not-deployed-not-started', version='historical-survivor-missing-cells-v1',
                    original_plan_sha256=sha(HERE/'plan.json'), original_expected_rows=40,
                    original_retained_rows=27, recovery_expected_rows=13, parent_denominators=[620,69,8],
                    available_row_audit_sha256=sha(HERE/'interrupted-audit.json'), cells=cells,
                    seconds=300, linux_cpus=[8], memory_mib=2048, perf=True, max_states=2000000,
                    outer_grace=0, repeat=1, original_order_seed=original['order_seed'],
                    validation=original['validation'], native_tools=original['native_tools'],
                    smpt_configurations=original['smpt_configurations'], verifypn=original['verifypn'],
                    required_file_sha256=required, minizinc_preflight=original['minizinc_preflight'],
                    uncommitted_missing_cell_artifacts=report['uncommitted_missing_cell_artifacts'],
                    changes='One invocation per missing cell, anchored exact-name filter, single selected method, fresh output directory. Original frozen runner, corpus, limits, binaries, native flags and SMPT modes. Timed native commands retain exact original arguments; external proof output paths change. Preflight/startup repeats outside recorded per-cell timing. Parent method/property rotation is preserved through explicit original sequence numbers.',
                    launch_gate='Deferred until new176cohort priority work and all live measurements terminate. No deployment or launch is authorized by running this preparer. Before explicit launch: fresh host/workload/unit check, original pins and repaired MiniZinc preflight, user lingering=yes, exclusive fresh recovery output/receipts. Changed pins require review; never silently replace binaries or scripts.',
                    service_lifecycle='Top-level systemd user service, no SSH-tied --wait or --pipe, Restart=no. ExecStopPost writes service terminal receipt; driver writes progress and terminal receipts. A machine reboot can prevent receipt creation. On any failure inspect boot ID, process/unit state and files; never infer completion from transport exit or automatically retry.',
                    reporting='Original experiment remains incomplete until separately audited recovery supplies precisely 13 missing keys. Preserve original 27 rows untouched. Report resumed-in-two-periods results and per-cell output provenance, never equivalence to uninterrupted execution or a stable speedup. Missing cells are unmeasured, not Unknown. Full unchanged auditor continues to reject the original27/40 output.',
                    prepare_source_sha256={str(p.relative_to(ROOT)):sha(p) for p in (Path(__file__), helper)})
    path = HERE / 'recovery-plan.json'
    path.write_text(json.dumps(recovery, indent=2) + '\n')
    driver = REMOTE + '/research/hard-survivors-current-v2/recovery-driver.py'
    python = REMOTE + '/vendor/venv/bin/python'
    stop = shlex.join([python, driver, '--record-service-terminal'])
    service = ['systemd-run','--user','--unit=pvass-hard-survivors-recovery-v1',
               '--property=Type=exec','--property=Restart=no','--property=KillMode=control-group',
               '--property=TimeoutStopSec=30','--property=RuntimeMaxSec=10800',
               '--property=WorkingDirectory='+REMOTE,
               '--property=StandardOutput=append:'+REMOTE+'/research/hard-survivors-current-v2/recovery-service.log',
               '--property=StandardError=inherit','--property=ExecStopPost='+stop,
               python, '-u', driver, '--execute', '--plan-sha256', sha(path)]
    (HERE/'recovery-service-command.json').write_text(json.dumps(dict(status='prepared-not-executed',command=service,recovery_plan_sha256=sha(path)),indent=2)+'\n')
    (HERE/'recovery-service-command.txt').write_text(shlex.join(service)+'\n')
    print(json.dumps(dict(status='prepared-not-started',missing_cells=len(cells),recovery_plan_sha256=sha(path))))


if __name__ == '__main__':
    main()
