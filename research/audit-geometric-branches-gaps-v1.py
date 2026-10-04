"""Reconcile saved diagnostic evidence without rerunning solvers or checkers."""
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/geometric-branches-gaps-v1'
PLAN = ROOT / 'research/geometric-branches-gaps-v1-plan.json'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


plan = read(PLAN)
environment = read(OUT / 'environment.json')
rows = [json.loads(line) for line in (OUT / 'runs.jsonl').read_text().splitlines()]
assert len(rows) == plan['expected_rows'] == 12
assert Counter((row['query'], row['method'], row['repeat']) for row in rows) == Counter(
    (query, method, 0) for query in plan['queries'] for method in plan['methods'])
for name, expected in plan['required_files'].items():
    assert sha(Path(name)) == expected, name
for key in ('seconds', 'repeat', 'outer_grace', 'memory_mib', 'max_states', 'order_seed'):
    assert environment[key] == plan[key], key
assert environment['geometric_branches_methods'] == ['geometric', 'combined']
assert environment['buffer_agglomeration_methods'] == ['buffer', 'combined']
assert environment['rust_original'] and not environment['perf']
checked = 0
for row in rows:
    assert row['execution_attempted'] and row['collection_status'] == 'imported'
    flags = plan['methods'][row['method']]
    for flag in ('--buffer-agglomeration', '--geometric-branches'):
        assert (flag in row['command']) == (flag in flags)
    binary = Path(row['command'][0])
    assert sha(binary) == environment['native_tools'][row['method']]['binary_sha256']
    assert row['command'][row['command'].index('--seconds') + 1] == '5.0'
    if row['verdict'] in ('reachable', 'unreachable'):
        assert row['exit_code'] == 0 and not row['outer_timeout']
        assert row['wall_seconds'] <= plan['seconds']
        assert not row['resources']['memory_limit_exceeded']
        raw = OUT / f"{row['query']}.{row['method']}.0.rust-original.json"
        answer = read(raw)
        saved = read(Path(str(raw) + '.validation-response.json'))
        for key in ('verdict', 'property_truth', 'independent_checks', 'branches', 'translation_check'):
            assert saved[key] == row[key], key
        assert answer['verdict'] == row['verdict']
        assert saved['independent_checks'] == ['python-witness']
        assert row['validation']['exit_code'] == 0 and not row['validation']['outer_timeout']
        checked += 1
summary = dict(
    rows=len(rows), queries=len(plan['queries']), saved_checked_definitive_rows=checked,
    solved={method: sum(row['method'] == method and row['verdict'] in ('reachable', 'unreachable') for row in rows)
            for method in plan['methods']},
    outer_timeouts=sum(row['outer_timeout'] for row in rows),
    registered_identities=len(plan['required_files']),
    outcomes=[{key: row[key] for key in ('query', 'method', 'verdict', 'wall_seconds', 'outer_timeout')} for row in rows],
    scope='Saved-evidence audit, not fresh proof checking. Outcome-selected three-query local diagnostic.',
)
(ROOT / 'research/geometric-branches-gaps-v1-verification.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2))
