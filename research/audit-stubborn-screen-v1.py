import collections
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from analyze_original_comparison import analyze

def read(path):
    return json.loads((ROOT / path).read_text())

def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()

plan = read('research/stubborn-screen-v1-plan.json')
env = read('results/stubborn-screen-v1/environment.json')
manifest = read('benchmarks/candidate-challenges-v1/manifest.json')
rows = [json.loads(x) for x in (ROOT / 'results/stubborn-screen-v1/runs.jsonl').read_text().splitlines()]
assert len(rows) == 208
assert set(env['property_order']) == {q['name'] for q in manifest['queries']}
for method, spec in plan['binaries'].items():
    assert sha(spec['path']) == spec['sha256'] == env['native_tools'][method]['binary_sha256']
    assert env['native_tools'][method]['engine'] == plan['methods'][method]
assert sha('results/solver-stubborn-v1/source.tar.gz') == plan['source_sha256']
assert sha('benchmarks/candidate-challenges-v1/manifest.json') == plan['manifest_sha256'] == env['manifest_sha256']
for name, digest in env['script_sha256'].items():
    path = Path('scripts') / name
    if not (ROOT / path).exists():
        path = Path(name)
    assert sha(path) == digest, name
for key in ['seconds', 'repeat', 'max_states', 'memory_mib', 'outer_grace', 'order_seed']:
    assert env[key] == plan[key], key
for row in rows:
    assert row['input_mode'] == 'rust-original-v1'
    command = row['command']
    assert command[command.index('--method') + 1] == plan['methods'][row['method']]
    assert float(command[command.index('--seconds') + 1]) == 5
    assert int(command[command.index('--max-states') + 1]) == 2000000
    assert row['resources']['memory_limit_bytes'] == 2048 * 1024**2
    if 'validation' in row:
        validation = row['validation']
        assert validation['seconds_limit'] == 30
        assert validation['memory_limit_bytes'] == 2048 * 1024**2
        assert validation['response_limit_bytes'] == 64 * 1024**2
        assert validation['dag_check_max_work'] == 20000000
        assert not validation['included_in_solver_timing']

for query in manifest['queries']:
    if 'family' not in query:
        assert query['suite'] == 'fastforward-repository-random_walk'
        query['family'] = 'FastForward/' + query['instance'].split('.')[0]
family = analyze(manifest, env, rows, 'family')
groups = collections.defaultdict(list)
for query in manifest['queries']:
    groups[tuple(sorted(b['sha256'] for b in query['branches']))].append(query['name'])
queries = {q['name']: q for q in manifest['queries']}
categories = {}
for category in sorted({q['challenge_category'] for q in manifest['queries']}):
    names = {n for n, q in queries.items() if q['challenge_category'] == category}
    categories[category] = dict(properties=len(names), solved={
        method: sum(r['query'] in names and r['method'] == method and r['verdict'] in {'reachable', 'unreachable'} for r in rows)
        for method in plan['methods']})
failures = [{k: r.get(k) for k in ['query', 'method', 'verdict', 'failure_stage', 'validation_failure', 'error']}
            for r in rows if r.get('failure_stage') or r.get('validation_failure') or r.get('error') or r['verdict'] == 'error']
report = dict(rows=len(rows), properties=len(queries), identities_and_limits_verified=True,
              checked_definitive_rows=sum(r['verdict'] in {'reachable', 'unreachable'} for r in rows),
              failures=failures, categories=categories, families=family['families'],
              resources={m: dict(outer_timeouts=sum(r['outer_timeout'] for r in rows if r['method'] == m),
                                 memory_limit_events=sum(bool(r['resources'].get('memory_limit_exceeded')) for r in rows if r['method'] == m))
                         for m in plan['methods']},
              exact_branch_duplicate_groups=[v for v in groups.values() if len(v) > 1],
              comparison=family['comparisons']['before -> after'],
              scope='One local five-second screen, no stable improvement claim; full parent denominator 620; reserved families untouched.',
              family_grouping='MCC/Boolean manifest families; FastForward instance basename before the first dot.')
(ROOT / 'research/stubborn-screen-v1-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
