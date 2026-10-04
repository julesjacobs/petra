#!/usr/bin/env python3
"""Audit frozen evidence only; does not execute solvers or proof checkers."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import random
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from analyze_original_comparison import analyze
from analyze_application_expansion import corpus_groups, failure_flags

NAME = 'buffer-agglomeration-application-v1'
folder = ROOT / 'results' / NAME
plan_path = ROOT / 'research' / f'{NAME}-plan.json'
frozen = ROOT / 'results/solver-buffer-agglomeration-v2'
DEFINITIVE = {'reachable', 'unreachable'}
hashes = {}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    path = path.resolve()
    if path not in hashes:
        with path.open('rb') as stream:
            hashes[path] = hashlib.file_digest(stream, 'sha256').hexdigest()
    return hashes[path]


def read(path):
    return json.loads(path.read_text())


def proof_chain(proof):
    result = []
    while isinstance(proof, dict):
        result.append(proof.get('kind', 'untyped'))
        proof = proof.get('inner')
    return result


plan = read(plan_path)
env = read(folder / 'environment.json')
corpus = ROOT / plan['corpus']
manifest = read(corpus / 'manifest.json')
rows = [json.loads(line) for line in (folder / 'runs.jsonl').read_text().splitlines()]
queries = {q['name']: q for q in manifest['queries']}
require(len(queries) == len(manifest['queries']) == plan['properties'] == 192, 'Property denominator')
require(len(rows) == plan['expected_rows'] == 384, 'Row denominator')
require(env['methods'] == list(plan['methods']) == ['control', 'buffer'], 'Methods')
require(env['buffer_agglomeration_methods'] == plan['buffer_agglomeration_methods'] == ['buffer'], 'Reduction flags')
require(env['target_zero_trap_methods'] == env['target_path_potential_methods'] == [], 'Other reduction flags')
require(plan['profiling'] is False, 'Profiling registration')
require(digest(corpus / 'manifest.json') == plan['manifest_sha256'] == env['manifest_sha256'], 'Manifest identity')
require(env['rust_original'] and env['track_resources'] and not env['native_original'] and not env['smpt_original'], 'Input/resource mode')
require(env['rust_original_methods'] == [] and env['linux_cpus'] is None and not env['perf'], 'Unexpected override')
for key in ('seconds', 'repeat', 'max_states', 'memory_mib', 'outer_grace', 'order_seed'):
    require(env[key] == plan[key], 'Environment differs: ' + key)
require((env['seconds'], env['repeat'], env['max_states'], env['memory_mib'], env['outer_grace']) == (5, 1, 2_000_000, 2048, 0), 'Limits')
validation_limits = dict(seconds=60, memory_mib=2048, response_mib=64, dag_check_max_work=200_000_000, included_in_solver_timing=False)
require(plan['validation'] == validation_limits and env['bounded_validation'] == dict(enabled=True, **validation_limits), 'Validation limits')
require(digest(frozen / 'vass-reach') == plan['binary_sha256'] == env['binary_sha256'], 'Binary identity')
require(digest(frozen / 'source.tar.gz') == plan['source_sha256'], 'Source archive identity')
for method in env['methods']:
    require(env['native_tools'][method] == dict(engine='portfolio-focused', binary=str(frozen / 'vass-reach'), binary_sha256=plan['binary_sha256']), 'Native identity: ' + method)
    require(plan['methods'][method] == 'portfolio-focused', 'Engine registration')
source_files = read(frozen / 'source-files-sha256.json')
provenance = read(frozen / 'provenance.json')
require(provenance['binary_sha256'] == plan['binary_sha256'] and provenance['source_sha256'] == plan['source_sha256'], 'Frozen provenance')
require(provenance['source_files'] == len(source_files) == 160, 'Frozen source count')
with tarfile.open(frozen / 'source.tar.gz') as archive:
    members = [m for m in archive.getmembers() if m.isfile()]
    require(len(members) == len(source_files) and {m.name for m in members} == set(source_files), 'Frozen archive membership')
    for member in members:
        with archive.extractfile(member) as stream:
            require(hashlib.file_digest(stream, 'sha256').hexdigest() == source_files[member.name], 'Frozen member: ' + member.name)
    cargo = archive.extractfile('Cargo.toml').read().decode()
    require('[patch.crates-io]' in cargo and 'vendor/varisat' in cargo, 'Patched varisat registration')
varisat_files = [name for name in source_files if name.startswith('vendor/varisat/')]
require(len(varisat_files) == 52, 'Vendored varisat membership')
for name, expected in provenance['review_sha256'].items():
    require(digest(frozen / 'review' / name) == expected, 'Frozen review: ' + name)
require(digest(Path(env['native_python'])) == env['native_python_sha256'], 'Validation Python identity')
runner_snapshots, extra_registered_scripts, current_runner_drift = [], [], []
for name, expected in env['script_sha256'].items():
    require(digest(folder / 'runner-source' / name) == expected, 'Runner snapshot: ' + name)
    if 'scripts/' + name in plan['required_file_sha256']:
        require(plan['required_file_sha256']['scripts/' + name] == expected, 'Runner registration: ' + name)
    else:
        require(name == 'requirements.txt', 'Unexpected unregistered runner snapshot')
    runner_snapshots.append(name)
for name, expected in plan['required_file_sha256'].items():
    if name.startswith('scripts/') and Path(name).name in env['script_sha256']:
        if digest(ROOT / name) != expected:
            current_runner_drift.append(name)
    else:
        require(digest(ROOT / name) == expected, 'Registered current artifact: ' + name)
        if name.startswith('scripts/'):
            extra_registered_scripts.append(name)
require(len(runner_snapshots) == 19 and len(extra_registered_scripts) == 94 and len(plan['required_file_sha256']) == 1009, 'Registered file counts')
require(env['queries'] == 192 and env['collection_counts'] == dict(planned=192, imported=192, unsupported=0, explicitly_unobserved=0), 'Collection denominator')
order = list(queries)
random.Random(plan['order_seed']).shuffle(order)
require(env['property_order'] == order, 'Shuffled property order')
expected_order = []
for i, name in enumerate(order):
    methods = env['methods'][i % 2:] + env['methods'][:i % 2]
    expected_order.extend((name, method, 0) for method in methods)
require([(r['query'], r['method'], r['repeat']) for r in rows] == expected_order, 'Matrix/order')
inputs = {}
for q in queries.values():
    require(q['status'] == 'imported' and q['planned'] and q['observed'], 'Collection status')
    pairs = [(corpus / q[k], q[k + '_sha256']) for k in ('net', 'property', 'pnml', 'xml')]
    pairs.extend((corpus / b['path'], b['sha256']) for b in q['branches'])
    for path, expected in pairs:
        require(digest(path) == expected, 'Input identity: ' + str(path))
        inputs[path.resolve()] = path.stat().st_size
require(env['input_preflight'] == dict(mode='streaming-deduplicated-sha256', unique_files=len(inputs), bytes_hashed=sum(inputs.values())), 'Input preflight')

proofs = {m: dict(outer=Counter(), nested=Counter(), chains=Counter(), independent_labels=Counter(), checked_verdicts=Counter()) for m in env['methods']}
raw_details, unknowns, validation_hashes = {}, [], {}
checked_branches_in_unknown_queries = []
validation_rows = 0
for r in rows:
    q, method = queries[r['query']], r['method']
    stem = f'{r["query"]}.{method}.0'
    command = [str(frozen / 'vass-reach'), '--pnml', str(corpus / q['pnml']), '--xml', str(corpus / q['xml']), '--property-id', q['property_id'], '--method', 'portfolio-focused', '--seconds', '5.0', '--max-states', '2000000']
    if method == 'buffer':
        command.append('--buffer-agglomeration')
    require(r['command'] == command, 'Command: ' + stem)
    require(r['input_mode'] == 'rust-original-v1' and r['suite'] == q['suite'] and r['property_kind'] == q['kind'], 'Input scope: ' + stem)
    require(r['execution_attempted'] and r['collection_status'] == 'imported' and r['collection_observed'] == q['observed'] and r['property_slot'] == q['property_slot'], 'Collection row: ' + stem)
    require(r['resources']['memory_limit_bytes'] == 2048 * 1024**2, 'Memory budget: ' + stem)
    if r['verdict'] in DEFINITIVE:
        require(not failure_flags(r) and not r['outer_timeout'] and r['wall_seconds'] <= 5 and r['exit_code'] == 0, 'Definitive answer failure/budget: ' + stem)
        require(r['property_truth'] == ((r['verdict'] == 'reachable') == (q['kind'] == 'EF')), 'Property polarity: ' + stem)
    else:
        require(r['property_truth'] is None, 'Unknown truth: ' + stem)
    answer = folder / (stem + '.rust-original.json')
    raw = read(answer)
    require(raw['kind'] == 'original-property-v1' and raw['property_id'] == q['property_id'] and raw['property_kind'] == q['kind'] and raw['branch_count'] == len(q['branches']), 'Raw input identity: ' + stem)
    details = []
    for attempt in raw['attempts']:
        out = attempt['outcome']
        details.append(dict(branch=attempt['branch'], verdict=out['verdict'], engine=out['method'], reason=out['reason'], proof_chain=proof_chain(out.get('proof'))))
    raw_details[stem] = dict(answer_sha256=digest(answer), raw_verdict=raw['verdict'], raw_deadline_exceeded=raw['deadline_exceeded'], attempts=details)
    if r['verdict'] not in DEFINITIVE:
        unknowns.append(dict(query=r['query'], method=method, wall_seconds=r['wall_seconds'], exit_code=r['exit_code'], outer_timeout=r['outer_timeout'], flags=sorted(failure_flags(r)), validation_saved='validation' in r, **raw_details[stem]))
    if 'validation' not in r:
        require(r['outer_timeout'] and r['verdict'] == 'unknown' and not r['branches'] and not r['independent_checks'], 'Missing validation: ' + stem)
        require(not Path(str(answer) + '.validation-request.json').exists() and not Path(str(answer) + '.validation-response.json').exists(), 'Unrecorded validation files: ' + stem)
        continue
    validation_rows += 1
    v = r['validation']
    for key, expected in dict(seconds_limit=60, memory_limit_bytes=2048 * 1024**2, response_limit_bytes=64 * 1024**2, dag_check_max_work=200_000_000, included_in_solver_timing=False).items():
        require(v[key] == expected, 'Validation limit: ' + stem + '/' + key)
    request_path, response_path = [Path(str(answer) + suffix) for suffix in ('.validation-request.json', '.validation-response.json')]
    request, response = read(request_path), read(response_path)
    validation_hashes[stem] = dict(request=digest(request_path), response=digest(response_path))
    require(request['query'] == q and request['corpus'] == str(corpus) and request['log'] == str(answer), 'Validation request identity: ' + stem)
    require(request['mode'] == 'rust-original-v1' and request['memory_bytes'] == v['memory_limit_bytes'] and request['response_bytes'] == v['response_limit_bytes'] and request['dag_check_max_work'] == v['dag_check_max_work'], 'Validation request bounds: ' + stem)
    require(request['exit_code'] == r['exit_code'] and request['outer_timeout'] == r['outer_timeout'], 'Validation execution identity: ' + stem)
    for key in ('verdict', 'property_truth', 'branches', 'independent_checks', 'translation_check', 'deadline_exceeded', 'rust_parse_seconds', 'rust_solve_seconds'):
        require(response.get(key) == r.get(key), 'Saved validation response: ' + stem + '/' + key)
    require(v['exit_code'] == 0 and not v['outer_timeout'] and not v['resources']['memory_limit_exceeded'] and v['wall_seconds'] <= 60, 'Saved checker failure: ' + stem)
    require(r['translation_check'] == 'independent-original-input-equals-all-canonical-branches', 'Translation label: ' + stem)
    require(raw['verdict'] == r['verdict'] and raw['property_truth'] == r['property_truth'] and raw['deadline_exceeded'] == r['deadline_exceeded'], 'Raw answer differs: ' + stem)
    require(raw['parse_seconds'] == r['rust_parse_seconds'] and raw['solve_seconds'] == r['rust_solve_seconds'], 'Raw timing: ' + stem)
    require(len(raw['attempts']) == len(r['branches']), 'Raw/checked branch count: ' + stem)
    indices = [b['branch'] for b in r['branches']]
    require(len(set(indices)) == len(indices) and set(indices) <= set(range(len(q['branches']))), 'Checked branch indices: ' + stem)
    require(r['independent_checks'] == [b['independent_check'] for b in r['branches']], 'Independent labels differ: ' + stem)
    for attempt, branch in zip(raw['attempts'], r['branches']):
        out = attempt['outcome']
        require((attempt['branch'], out['verdict'], out['method']) == (branch['branch'], branch['verdict'], branch['engine']), 'Raw/checked branch identity: ' + stem)
        if branch['verdict'] not in DEFINITIVE:
            continue
        label = branch['independent_check']
        require(label.startswith('python-'), 'Unchecked definitive branch: ' + stem)
        proofs[method]['independent_labels'][label] += 1
        proofs[method]['checked_verdicts'][branch['verdict']] += 1
        if r['verdict'] not in DEFINITIVE:
            checked_branches_in_unknown_queries.append(dict(query=r['query'], method=method, **branch))
        if branch['verdict'] == 'unreachable':
            chain = proof_chain(out.get('proof')) or ['legacy-certificate']
            proofs[method]['outer'][chain[0]] += 1
            proofs[method]['nested'].update(chain[1:])
            proofs[method]['chains'][' -> '.join(chain)] += 1

summary = analyze(manifest, env, rows, 'family')
matrix = {(r['query'], r['method']): r for r in rows}
groups = corpus_groups(manifest)
require(len(groups) == plan['exact_ordered_branch_representatives'] == 187, 'Ordered representatives')
duplicate_groups = []
for group in groups:
    if len(group) == 1:
        continue
    verdicts = {matrix[n, m]['verdict'] for n in group for m in env['methods']} & DEFINITIVE
    require(len(verdicts) <= 1, 'Duplicate definitive disagreement')
    duplicate_groups.append(dict(representative=group[0], queries=group, property_kinds=sorted({queries[n]['kind'] for n in group}), verdicts={m:{n:matrix[n,m]['verdict'] for n in group} for m in env['methods']}))
representative_solved = {m: sum(matrix[group[0], m]['verdict'] in DEFINITIVE for group in groups) for m in env['methods']}
comparison = summary['comparisons']['control -> buffer']
changed = [{k: matrix[n,m].get(k) for k in ('query', 'method', 'verdict', 'wall_seconds', 'outer_timeout', 'branches')} for n in comparison['gained'] + comparison['lost'] for m in env['methods']]
launch = ROOT / 'research' / f'run-{NAME}.sh'
require('unset VASS_RELAXED_PROFILE VASS_PORTFOLIO_PROFILE' in launch.read_text(), 'Profiling launcher')
sources = {str(p.relative_to(ROOT)): digest(p) for p in (plan_path, folder / 'environment.json', folder / 'runs.jsonl', corpus / 'manifest.json', launch, Path(__file__), ROOT / 'scripts/analyze_original_comparison.py', ROOT / 'scripts/analyze_application_expansion.py')}
report = dict(rows=len(rows), properties=len(queries), identities_and_limits_verified=True, solved=summary['stable_solved'], counts=summary['counts'], families=summary['families'], comparison=comparison, changed_cases=changed,
    exact_ordered_branch_representatives=len(groups), representative_solved=representative_solved, duplicate_groups=duplicate_groups,
    representative_scope='Lexicographically first query per exact ordered canonical branch SHA256 tuple; no semantic or isomorphism deduplication; no outcome selection.',
    input_files_hashed=len(inputs), input_bytes_hashed=sum(inputs.values()), registered_files_verified=len(plan['required_file_sha256']), runner_snapshots_verified=len(runner_snapshots), current_extra_scripts_verified=len(extra_registered_scripts), current_extra_scripts=extra_registered_scripts, current_runner_drift=current_runner_drift,
    frozen_source_files_verified=len(source_files), frozen_varisat_files_verified=len(varisat_files), frozen_review_files_verified=len(provenance['review_sha256']),
    validation_rows=validation_rows, definitive_rows=sum(r['verdict'] in DEFINITIVE for r in rows), saved_checked_branch_evidence=proofs, checked_branches_in_unknown_queries=checked_branches_in_unknown_queries,
    failures=[dict(query=r['query'], method=r['method'], flags=sorted(failure_flags(r))) for r in rows if failure_flags(r)], unknowns=unknowns,
    resources={m:dict(outer_timeouts=sum(r['outer_timeout'] for r in rows if r['method']==m), memory_limit_events=sum(bool(r['resources'].get('memory_limit_exceeded')) for r in rows if r['method']==m), nonzero_exits=sum(r['exit_code'] != 0 for r in rows if r['method']==m)) for m in env['methods']},
    residual_shared_unknown=[n for n in order if all(matrix[n,m]['verdict'] not in DEFINITIVE for m in env['methods'])],
    raw_answers=raw_details, validation_file_sha256=validation_hashes, sources=sources,
    no_definitive_disagreements=True, fresh_proof_checks=0,
    scope='Complete single-repeat local development regression after outcome-selected NoC diagnosis. Same frozen binary, buffer flag only. Saved independent-check responses and identities audited; proof checking and solvers were not rerun. Not held-out evaluation, competitor comparison, stable speed evidence, or default-promotion evidence.',
    provenance_scope='19 measured runner snapshots verified against environment hashes; 18 also match plan registration (requirements.txt was not plan-pinned). 94 other registered scripts verified only at their current paths. Later live changes to snapshotted runners are reported separately and do not replace measured snapshots.',
    profiling_scope='Registered off; launcher unsets both profile flags. Positive engine labels alone do not establish reduction applicability; negative proof wrappers explicitly record reductions.',
    memory_scope='Sampled macOS process-tree RSS, not a hard memory cap; zero observed excesses cannot establish absence of transient spikes.')
(ROOT / 'research' / f'{NAME}-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k:report[k] for k in ('rows','properties','solved','counts','comparison','representative_solved','input_files_hashed','input_bytes_hashed','registered_files_verified','runner_snapshots_verified','current_extra_scripts_verified','current_runner_drift','validation_rows','definitive_rows','saved_checked_branch_evidence','resources','residual_shared_unknown')}, indent=2))
