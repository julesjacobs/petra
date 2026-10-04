"""Audit saved phase-pair qualification; does not rerun any solver or proof checker."""
import hashlib
import json
import tarfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/local-phase-pair-survivors-v1'
CORPUS = ROOT / 'research/application-ladder-qualification-v1/stage-300'
METHODS = {'native-phase-pair': 'phase-pair', 'native-batched': 'portfolio-batched'}

def read(path):
    return json.loads(path.read_text())

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def audit_archive(folder, archive, listing):
    expected = read(folder / listing)
    with tarfile.open(folder / archive) as source:
        files = [m for m in source.getmembers() if m.isfile()]
        assert len(files) == len(expected) and {m.name for m in files} == set(expected)
        for member in files:
            with source.extractfile(member) as stream:
                assert hashlib.file_digest(stream, 'sha256').hexdigest() == expected[member.name], member.name

plan_path = ROOT / 'research/phase-pair-survivors-v1-plan.json'
plan = read(plan_path)
execution = read(ROOT / 'research/phase-pair-survivors-v1-execution.json')
assert execution['plan_sha256'] == sha(plan_path)
assert read(ROOT / 'research/phase-pair-survivors-v1-terminal.json')['exit_code'] == 0
for name, digest in plan['file_sha256'].items():
    assert sha(ROOT / name) == digest, name
audit_archive(ROOT / 'results/solver-phase-pair-v1', 'source.tar.gz', 'source-files-sha256.json')
audit_archive(ROOT / 'results/runner-phase-pair-v1', 'runner.tar.gz', 'files-sha256.json')
env = read(OUT / 'environment.json')
for name, digest in env['script_sha256'].items():
    assert sha(OUT / 'runner-source' / name) == digest == plan['file_sha256']['results/runner-phase-pair-v1/source/scripts/' + name]
assert env['seconds'] == 30 and env['repeat'] == 1 and env['memory_mib'] == 2048
assert env['max_states'] == 2000000 and env['outer_grace'] == 0 and env['rust_original']
assert env['buffer_agglomeration_methods'] == ['native-batched']
assert env['bounded_validation'] == dict(enabled=True, seconds=60.0, memory_mib=2048, response_mib=64, dag_check_max_work=200000000, included_in_solver_timing=False)
assert set(env['methods']) == set(METHODS) == set(env['native_tools'])
for name, tool in env['native_tools'].items():
    assert sha(Path(tool['binary'])) == tool['binary_sha256'] == plan['binary_sha256']
    assert tool['engine'] == METHODS[name]
manifest = read(CORPUS / 'manifest.json')
assert sha(CORPUS / 'manifest.json') == env['manifest_sha256']
queries = {q['name']: q for q in manifest['queries']}
assert set(queries) == set(plan['queries']) and len(queries) == 4
for q in queries.values():
    for field in ['net', 'property', 'pnml', 'xml']:
        if field in q:
            assert sha(CORPUS / q[field]) == q[field + '_sha256']
    for branch in q['branches']:
        assert sha(CORPUS / branch['path']) == branch['sha256']
rows = [json.loads(line) for line in (OUT / 'runs.jsonl').read_text().splitlines()]
assert len(rows) == plan['rows'] == 8
assert {(r['query'], r['method'], r['repeat']) for r in rows} == {(q, m, 0) for q in queries for m in METHODS}
verdicts = defaultdict(set)
details = []
for row in rows:
    q = queries[row['query']]
    label = f"{row['query']}.{row['method']}.0.rust-original.json"
    answer_path = OUT / label
    assert row['collection_status'] == 'imported' and row['execution_attempted']
    assert row['input_mode'] == 'rust-original-v1'
    command = row['command']
    assert command[0] == env['native_tools'][row['method']]['binary']
    for flag, value in [('--method', METHODS[row['method']]), ('--seconds', '30.0'), ('--max-states', '2000000'), ('--property-id', q['property_id'])]:
        assert command[command.index(flag) + 1] == value
    for flag, field in [('--pnml', 'pnml'), ('--xml', 'xml')]:
        assert Path(command[command.index(flag) + 1]).resolve() == (CORPUS / q[field]).resolve()
    assert ('--buffer-agglomeration' in command) == (row['method'] == 'native-batched')
    assert row['resources']['memory_limit_bytes'] == 2048 * 1024**2
    if 'validation' in row:
        request = read(OUT / (label + '.validation-request.json'))
        assert request['query'] == q and request['mode'] == 'rust-original-v1'
        assert request['log'] == str(answer_path) and request['corpus'] == str(CORPUS) and request['artifacts'] == str(OUT)
        assert request['exit_code'] == row['exit_code'] and request['outer_timeout'] == row['outer_timeout']
        validation = row['validation']
        assert validation['seconds_limit'] == 60 and validation['memory_limit_bytes'] == 2048 * 1024**2
        assert validation['response_limit_bytes'] == 64 * 1024**2 and not validation['included_in_solver_timing']
        if validation['exit_code'] == 0 and not validation['outer_timeout']:
            response = read(OUT / (label + '.validation-response.json'))
            assert all(row.get(key) == value for key, value in response.items())
    detail = {key: row[key] for key in ['query', 'method', 'verdict', 'property_truth', 'wall_seconds', 'exit_code', 'outer_timeout']}
    detail['memory_limit_exceeded'] = row['resources']['memory_limit_exceeded']
    if row['verdict'] in ['reachable', 'unreachable']:
        verdicts[row['query']].add(row['verdict'])
        assert row['method'] == 'native-phase-pair' and row['verdict'] == 'unreachable'
        assert row['exit_code'] == 0 and not row['outer_timeout'] and not detail['memory_limit_exceeded']
        assert validation['exit_code'] == 0 and not validation['outer_timeout'] and not validation['resources']['memory_limit_exceeded']
        assert row['translation_check'] == 'independent-original-input-equals-all-canonical-branches'
        answer = read(answer_path)
        assert answer['verdict'] == row['verdict'] and not answer['deadline_exceeded']
        assert answer['property_id'] == q['property_id'] and answer['property_kind'] == q['kind']
        assert row['property_truth'] == answer['property_truth'] == (q['kind'] == 'AG')
        assert answer['branch_count'] == len(q['branches']) == len(row['branches'])
        assert {b['branch'] for b in row['branches']} == set(range(len(q['branches'])))
        assert all(b['verdict'] == 'unreachable' and b['independent_check'] == 'python-phase-pair-closure' for b in row['branches'])
        assert len(answer['attempts']) == len(q['branches'])
        assert all(a['outcome']['proof']['kind'] == 'phase-pair-closure-v1' for a in answer['attempts'])
        detail['checker_seconds'] = validation['wall_seconds']
        detail['answer_file_bytes'] = answer_path.stat().st_size
        detail['proof_json_bytes_compact'] = sum(len(json.dumps(a['outcome']['proof'], separators=(',', ':')).encode()) for a in answer['attempts'])
    elif row['method'] == 'native-phase-pair':
        answer = read(answer_path)
        detail['reasons'] = [a['outcome']['reason'] for a in answer['attempts']]
        assert all(reason == 'pair relation size limit' for reason in detail['reasons'])
    details.append(detail)
assert all(len(v) <= 1 for v in verdicts.values())
report = dict(status='passed', rows=len(rows), queries=len(queries), parent_denominators=plan['parent_denominators'],
              coverage={m: dict(Counter(r['verdict'] for r in rows if r['method'] == m)) for m in METHODS},
              checked_definitive_rows=sum(r['verdict'] in ['reachable', 'unreachable'] for r in rows), details=details,
              artifact_sha256={str(p.relative_to(ROOT)): sha(p) for p in OUT.rglob('*') if p.is_file()},
              scope='Saved evidence reconciliation, not a new proof execution. Full four-query selected survivor cohort; local 30s comparison. No cross-machine speed or general superiority claim.')
for p in [plan_path, Path(__file__), ROOT / 'research/phase-pair-survivors-v1-terminal.json']:
    report['artifact_sha256'][str(p.relative_to(ROOT))] = sha(p)
(ROOT / 'research/phase-pair-survivors-v1-audit.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k != 'artifact_sha256'}, indent=2))
