"""Register the complete union of two existing development cohorts."""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REMOTE = '/home/jules/experiments/pvass-publication/'
CORPUS = 'benchmarks/application-portfolio-comparison-v1'


def read(name):
    return json.loads((ROOT / name).read_text())


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


queries = []
parents = {}
for name in ('application-expansion-v1', 'application-parameter-ladders-v2'):
    path = f'benchmarks/{name}/manifest.json'
    parents[path] = sha(ROOT / path)
    for original in read(path)['queries']:
        query = copy.deepcopy(original)
        query['parent_corpus'] = name
        for key in ('net', 'property', 'pnml', 'xml'):
            if key in query:
                query[key] = f'../{name}/' + query[key]
        for branch in query.get('branches', []):
            branch['path'] = f'../{name}/' + branch['path']
        queries.append(query)
assert len(queries) == len({query['name'] for query in queries}) == 656
assert sum(query['status'] == 'imported' for query in queries) == 640
groups = {tuple(branch['sha256'] for branch in query['branches'])
          for query in queries if query['status'] == 'imported'}
assert len(groups) == 629
corpus = ROOT / CORPUS
corpus.mkdir()
manifest = dict(format='application-cohort-union-v1', collection_complete=True,
                expected_properties=656, parents=parents,
                scope='Complete existing development cohorts; no new or reserved payloads.', queries=queries)
(corpus / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
base = read('research/application-parameter-ladders-v2-screen-plan.json')
required = base['required_file_sha256']
required.update({name: digest for name, digest in read('research/application-expansion-v1-screen-plan.json')['required_file_sha256'].items()
                 if name.startswith('benchmarks/application-expansion-v1/')})
required = {name: digest for name, digest in required.items() if not name.startswith('scripts/')}
required.update(read('results/runner-repeated-search-v2/files-sha256.json'))
new = 'results/linux-solver-repeated-search-v1/vass-reach'
old = base['native_binary']
new_hash = sha(ROOT / new)
native = {
    'native-frozen': dict(engine='portfolio-focused', binary=REMOTE + old, binary_sha256=base['native_binary_sha256']),
    'native-buffer': dict(engine='portfolio-focused', binary=REMOTE + new, binary_sha256=new_hash),
    'native-batched': dict(engine='portfolio-batched', binary=REMOTE + new, binary_sha256=new_hash),
}
for name in ('vass-reach', 'source.tar.gz', 'source-files-sha256.json', 'provenance.json',
             'test-fixtures.tar.gz', 'test-fixtures-sha256.json', 'tests.log', 'build.log',
             'tests-initial-missing-fixtures.log'):
    path = Path(new).parent / name
    required[str(path)] = sha(ROOT / path)
for name in ('source.tar.gz', 'SHA256SUMS'):
    path = Path(old).parent / name
    required[str(path)] = sha(ROOT / path)
for name in ('runner.tar.gz', 'files-sha256.json'):
    path = Path('results/runner-repeated-search-v2') / name
    required[str(path)] = sha(ROOT / path)
for name in (CORPUS + '/manifest.json', 'research/prepare-application-portfolio-comparison-v1.py',
             'research/run-linux-application-portfolio-comparison-v1.sh', 'research/linux-repeated-search-smoke-v1-verification.json',
             'research/portfolio-comparison-protocol-review.md', 'results/linux-repeated-search-smoke-v1/runs.jsonl',
             'results/linux-repeated-search-smoke-v1/environment.json'):
    required[name] = sha(ROOT / name)
base.update(
    corpus=CORPUS, manifest_sha256=sha(corpus / 'manifest.json'),
    properties=656, expected_rows=3280, source_properties=656, parent_properties=656,
    imported_properties=640, collection_failed_properties=16,
    exact_ordered_branch_representatives=629, native_tools=native,
    native_binary=new, native_binary_sha256=new_hash,
    methods={**{name: tool['engine'] for name, tool in native.items()},
             'verifypn-default': 'default', 'smpt-full-portable': 'full portable'},
    target_zero_trap_methods=[], target_path_potential_methods=[], geometric_branches_methods=[],
    buffer_agglomeration_methods=['native-buffer', 'native-batched'],
    required_file_sha256=required,
    selection_evidence=parents,
    output='results/linux-application-portfolio-comparison-v1', order_seed=20261109,
    scope='Complete union of192prior application properties and464ladder slots.656slots,640imports,629ordered-branch representatives;3280rows,3200solver invocations.',
    candidate_scope='Frozen capacity-direct focused baseline; same new binary focused+buffer and batched+buffer; VerifyPN default; repaired SMPT full portable. Old versus new is an end-to-end comparison; only the same-binary buffer versus batched pair isolates repeated firing.',
    runner_scope='New explicitly deployed22-file dependency closure in results/runner-repeated-search-v2. Prior remote bytes preserved; all22runtime files recorded and snapshotted.',
    reporting='Report full656slots and640imports separately, both parent cohorts, all families and exact representatives, every failed import, timeout, checker failure and disagreement. One repetition is a development screen, not stable timing or held-out superiority.',
    followup='Qualify all13jointly unresolved imported queries selected from the earlier ladder screen under longer budgets, retaining their full parent. Do not select survivors anew to erase prior failures.',
    smoke_evidence='research/linux-repeated-search-smoke-v1-verification.json',
    status='registered-not-started')
path = ROOT / 'research/application-portfolio-comparison-v1-plan.json'
with path.open('x') as stream:
    json.dump(base, stream, indent=2, sort_keys=True)
    stream.write('\n')
print(json.dumps(dict(properties=656, imports=640, representatives=629, expected_rows=3280,
                      registered_files=len(required), plan_sha256=sha(path))))
