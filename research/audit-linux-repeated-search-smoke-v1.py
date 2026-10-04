"""Check saved capability evidence; no solver or checker reruns."""
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/linux-repeated-search-smoke-v1'
PLAN = ROOT / 'research/linux-repeated-search-smoke-v1-plan.json'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


plan = read(PLAN)
environment = read(OUT / 'environment.json')
rows = [json.loads(line) for line in (OUT / 'runs.jsonl').read_text().splitlines()]
queries = {'CircadianClock-PT-100000__RC12', 'NoC3x3-PT-8B__RC12', 'IOTPpurchase-PT-C05M04P03D02__RC13'}
methods = ['native-frozen', 'native-buffer', 'native-batched', 'verifypn-default', 'smpt-full-portable']
assert len(rows) == plan['expected_rows'] == 15
assert Counter((row['query'], row['method'], row['repeat']) for row in rows) == Counter(
    (query, method, 0) for query in queries for method in methods)
assert environment['methods'] == methods
assert environment['buffer_agglomeration_methods'] == ['native-buffer', 'native-batched']
assert environment['target_zero_trap_methods'] == environment['target_path_potential_methods'] == environment['geometric_branches_methods'] == []
runner = read(ROOT / 'results/runner-repeated-search-v2/files-sha256.json')
assert set(environment['script_sha256']) == {Path(name).name for name in runner}
for name, expected in runner.items():
    assert sha(OUT / 'runner-source' / Path(name).name) == environment['script_sha256'][Path(name).name] == expected
matrix = {(row['query'], row['method']): row for row in rows}
checks = []
for row in rows:
    resource = row['resources']
    assert resource['runner'] == 'linux-systemd-user' and resource['cpus'] == [8]
    assert resource['memory_limit_bytes'] == 2048 * 1024**2 and resource['perf_enabled']
    if row['method'].startswith('native-'):
        expected = environment['native_tools'][row['method']]
        relative = expected['binary'].removeprefix('/home/jules/experiments/pvass-publication/')
        assert sha(ROOT / relative) == expected['binary_sha256'] == plan['required_file_sha256'][relative]
        assert row['command'][0] == expected['binary']
        assert ('--buffer-agglomeration' in row['command']) == (row['method'] != 'native-frozen')
        if row['verdict'] in ('reachable', 'unreachable'):
            assert row['exit_code'] == 0 and not row['outer_timeout'] and row['wall_seconds'] <= 5
            response = read(OUT / f"{row['query']}.{row['method']}.0.rust-original.json.validation-response.json")
            assert all(row[key] == response[key] for key in ('verdict', 'property_truth', 'branches', 'independent_checks', 'translation_check'))
            assert row['validation']['exit_code'] == 0 and not row['validation']['outer_timeout']
            assert all(check.startswith('python-') for check in row['independent_checks'])
            checks.extend(row['independent_checks'])
for method in ('native-buffer', 'native-batched'):
    assert matrix[('NoC3x3-PT-8B__RC12', method)]['independent_checks'] == ['python-witness']
    assert matrix[('IOTPpurchase-PT-C05M04P03D02__RC13', method)]['independent_checks'] == ['python-buffer-agglomeration']
assert matrix[('CircadianClock-PT-100000__RC12', 'native-batched')]['independent_checks'] == ['python-witness']
assert matrix[('IOTPpurchase-PT-C05M04P03D02__RC13', 'native-frozen')]['independent_checks'] == ['python-causal-state-equation']
for row in rows:
    if row['method'] == 'smpt-full-portable':
        assert not row.get('capability_failures')
        if row['verdict'] in ('reachable', 'unreachable'):
            assert not row.get('subprocess_error') and row['exit_code'] == 0
report = dict(status='passed', rows=15, saved_native_check_counts=dict(Counter(checks)),
              runner_files=len(runner), runs_sha256=sha(OUT / 'runs.jsonl'),
              environment_sha256=sha(OUT / 'environment.json'),
              scope='Capability smoke with original-input witnesses and negative checks. Not competitive timing evidence.')
(ROOT / 'research/linux-repeated-search-smoke-v1-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
