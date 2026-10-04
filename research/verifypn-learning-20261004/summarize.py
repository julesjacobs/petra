#!/usr/bin/env python3
"""Replay the frozen audit, normalizing JSON tuples before receipt comparison."""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('frozen_audit', HERE / 'audit.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
folder = HERE / 'full-v3'
plan = json.loads((folder / 'plan.json').read_text())
blocks = {}
for stage in ('repeat1', 'repeat2'):
    result, rows = audit.audit_stage(folder, plan, stage)
    result = json.loads(json.dumps(result))
    path = folder / (stage + '-audit.json')
    if path.exists():
        audit.require(json.loads(path.read_text()) == result, 'Saved audit differs: ' + stage)
    else:
        audit.run.save(path, result)
    audit.require(result['status'] == 'passed', 'Audit failed: ' + stage)
    blocks[stage] = result, rows
    print(json.dumps(dict(stage=stage, status=result['status'], rows=result['rows'],
                          accepted=result['accepted_definitive_rows'])), flush=True)
report = audit.summary(folder, plan, blocks)
audit.run.save(folder / 'analysis-receipt.json', dict(
    plan_sha256=audit.run.sha(folder / 'plan.json'),
    summarizer_sha256=audit.run.sha(Path(__file__)),
    frozen_audit_sha256=audit.run.sha(HERE / 'audit.py'),
    frozen_runner_sha256=audit.run.sha(HERE / 'run.py'),
    audit_receipts={stage: audit.run.sha(folder / (stage + '-audit.json')) for stage in blocks},
    summary_sha256=audit.run.sha(folder / 'summary.json'),
    report_sha256=audit.run.sha(folder / 'REPORT.md'),
    amendment='The frozen audit compares deserialized duplicate-group lists with in-memory tuples. This entry point normalizes the freshly recomputed result through JSON before equality comparison. No admission, accounting, source pin, measurement, or host-policy rule changes.'))
print(json.dumps(dict(status=report['status'], stable_gains=len(report['stable_gains']),
                      stable_losses=len(report['stable_losses']))))
