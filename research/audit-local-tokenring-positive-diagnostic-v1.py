"""Reconcile the completed diagnostic; no solver or checker execution."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


plan_path = ROOT / 'research/local-tokenring-positive-diagnostic-v1-plan.json'
plan = json.loads(plan_path.read_text())
output = ROOT / 'results/local-tokenring-positive-diagnostic-v1'
environment = json.loads((output / 'environment.json').read_text())
rows = [json.loads(line) for line in (output / 'runs.jsonl').read_text().splitlines()]
for name, digest in plan['file_sha256'].items():
    assert sha(ROOT / name) == digest, name
for name, digest in environment['script_sha256'].items():
    assert sha(output / 'runner-source' / name) == digest, name
assert len(rows) == 12
assert {(r['query'], r['method'], r['repeat']) for r in rows} == {
    (q, method, 0) for q in plan['queries'] for method in environment['native_tools']}
assert environment['seconds'] == 5 and environment['memory_mib'] == 2048
assert environment['bounded_validation']['enabled']
for method in environment['native_tools'].values():
    assert sha(Path(method['binary'])) == method['binary_sha256']
observations = []
for row in rows:
    assert row['verdict'] == 'unknown' and row['outer_timeout']
    assert row['collection_status'] == 'imported' and row['execution_attempted']
    path = output / f"{row['query']}.{row['method']}.0.rust-original.json"
    record = dict(query=row['query'], method=row['method'], verdict=row['verdict'],
                  outer_timeout=row['outer_timeout'], wall_seconds=row['wall_seconds'],
                  exit_code=row['exit_code'])
    try:
        answer = json.loads(path.read_text())
    except json.JSONDecodeError:
        record['answer_status'] = 'incomplete'
    else:
        assert answer['verdict'] == 'unknown'
        record.update(answer_status='complete-unknown', parse_seconds=answer.get('parse_seconds'),
                      solve_seconds=answer.get('solve_seconds'),
                      attempts=[{k: a['outcome'].get(k) for k in ['method', 'states', 'reason']}
                                for a in answer.get('attempts', [])])
    observations.append(record)
artifacts = {str(p.relative_to(ROOT)): sha(p) for p in output.rglob('*') if p.is_file()}
artifacts[str(plan_path.relative_to(ROOT))] = sha(plan_path)
profile = ROOT / 'results/local-tokenring-positive-profile-v1'
artifacts.update({str(p.relative_to(ROOT)): sha(p) for p in profile.iterdir() if p.is_file()})
report = dict(status='passed', rows=12, checked_definitive_rows=0, observations=observations,
              artifact_sha256=artifacts,
              scope='Read-only artifact reconciliation of twelve Unknown rows; no definitive answers or checks to replay. Three selected queries from nine competitor-only gaps. Profiles remain separate diagnostic observations; no competitive timing claim.')
(ROOT / 'research/local-tokenring-positive-diagnostic-v1-verification.json').write_text(json.dumps(report, indent=2)+'\n')
print('Passed: 12/12 rows retained; all Unknown at outer deadline; 10 complete Unknown answers and two incomplete outputs.')
