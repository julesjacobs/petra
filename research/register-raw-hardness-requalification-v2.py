"""Register the unchanged full raw cohorts with the current frozen solver/checker."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def sha(name):
    with (ROOT / name).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

plan = json.loads((ROOT / 'research/raw-hardness-requalification-v1-plan.json').read_text())
plan.update(format='raw-hardness-requalification-v2', status='registered-not-started',
            scope='Full two-cohort development requalification after exact control sharing, typed proof streaming and sparse duplicate-node keys. Same28source slots/24unique programs;60s including independent checking and sampled2GiB. No competitive timing claim.',
            methods=['raw-negative', 'raw-portfolio'])
plan.pop('identical_raw_source_modules', None)
plan['raw_dispatch'] = 'Frozen streamed/shared solver: raw-negative directly; raw-portfolio retains its quarter-time negative schedule and positive continuation.'
binary = 'results/solver-raw-proof-streaming-v1/vass-reach'
archive = 'results/solver-raw-proof-streaming-v1/source.tar.gz'
plan['configurations'] = {'streamed-shared': dict(binary=binary, binary_sha256=sha(binary), archive=archive, archive_sha256=sha(archive))}
plan['limits'].update(seconds=60, repeat=1, max_states=100_000_000, negative_verifier_work_limit=10_000_000_000)
plan['runs'] = []
for cohort, corpus in [('diverse', 'raw-diverse-automaton-v1'), ('scaling', 'raw-diverse-scaling-automaton-v1')]:
    output = f'results/raw-hardness-requalification-v2-{cohort}'
    command = [str(ROOT / 'vendor/venv/bin/python'), str(ROOT / 'scripts/benchmark_stress_raw.py'),
               '--corpus', str(ROOT / 'benchmarks' / corpus), '--output', str(ROOT / output),
               '--binary', str(ROOT / binary), '--methods', *plan['methods'], '--all-sources',
               '--seconds', '60', '--memory-mib', '2048', '--repeat', '1',
               '--solver-fraction', '0.8', '--max-states', '100000000']
    plan['runs'].append(dict(cohort=cohort, configuration='streamed-shared', output=output,
                             expected_rows=2 * len(plan['cohorts'][cohort]['sources']), command=command))
names = set(plan['file_sha256']) | {binary, archive,
        'results/solver-raw-proof-streaming-v1/provenance.json',
        'research/register-raw-hardness-requalification-v2.py',
        'research/raw-hardness-requalification-v2-launch.py',
        'research/raw-checker-sparse-identity-tests.log',
        'research/raw-checker-end-to-end-v1-verification.json',
        'scripts/test_raw_invariant_check.py'}
plan['file_sha256'] = {name: sha(name) for name in sorted(names)}
plan['checker_change'] = 'Dense controller tuples for duplicate detection replaced by exact sparse position/value tuples after unchanged full u64/dimension validation; certificate/schema/transition/affine checks retained. Frozen runner snapshots record changed checker bytes.'
plan['expected_rows'] = sum(run['expected_rows'] for run in plan['runs'])
assert plan['expected_rows'] == 56
with (ROOT / 'research/raw-hardness-requalification-v2-plan.json').open('x') as stream:
    json.dump(plan, stream, indent=2)
    stream.write('\n')
print('Registered56rows over28source slots/24unique programs; one export failure retained per method.')
