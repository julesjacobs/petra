import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from process_runner import workspace_workloads


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


corpus = ROOT / 'benchmarks/application-gaps-v2'
binary = ROOT / 'results/solver-repeated-search-v1/vass-reach'
output = ROOT / 'results/repeated-search-gaps-v1'
manifest = json.loads((corpus / 'manifest.json').read_text())
assert len(manifest['queries']) == 3
paths = {str(binary): sha(binary), str(corpus / 'manifest.json'): sha(corpus / 'manifest.json')}
for query in manifest['queries']:
    for key, value in query.items():
        if key.endswith('_sha256') and key[:-7] in query:
            path = (corpus / query[key[:-7]]).resolve()
            assert sha(path) == value
            paths[str(path)] = value
    for branch in query['branches']:
        path = (corpus / branch['path']).resolve()
        assert sha(path) == branch['sha256']
        paths[str(path)] = branch['sha256']
for path in (ROOT / 'scripts').glob('*.py'):
    paths[str(path)] = sha(path)
for name in ('source.tar.gz', 'source-files-sha256.json', 'provenance.json'):
    path = binary.parent / name
    paths[str(path)] = sha(path)
paths[str(Path(__file__).resolve())] = sha(Path(__file__).resolve())
methods = {'control': [], 'buffer': ['--buffer-agglomeration'],
           'batched': [],
           'combined': ['--buffer-agglomeration']}
plan = dict(
    scope='Outcome-selected three-query development diagnostic, complete four-way factorial. One local repetition; no held-out, competitor or stable speed claim.',
    queries=[query['name'] for query in manifest['queries']], methods=methods,
    engines={method: ('portfolio-batched' if method in ('batched', 'combined') else 'portfolio-focused') for method in methods}, seconds=5, repeat=1, outer_grace=0, memory_mib=2048,
    memory_enforcement='sampled macOS process-tree RSS', max_states=2_000_000,
    validation=dict(seconds=60, memory_mib=2048, response_mib=64, dag_work=200_000_000),
    expected_rows=12, profiling=False, order_seed=20261106, required_files=paths,
)
assert not output.exists() and not workspace_workloads(ROOT)
with (ROOT / 'research/repeated-search-gaps-v1-plan.json').open('x') as stream:
    json.dump(plan, stream, indent=2)
    stream.write('\n')
command = [sys.executable, '-u', 'scripts/benchmark_smpt_classic.py',
           '--corpus', str(corpus), '--binary', str(binary)]
for method in methods:
    command += ['--native-tool', method, plan['engines'][method], str(binary)]
command += ['--methods', *methods,
            '--buffer-agglomeration-method', 'buffer', '--buffer-agglomeration-method', 'combined',
            '--rust-original', '--bounded-validation', '--validation-seconds', '60',
            '--validation-memory-mib', '2048', '--validation-response-mib', '64',
            '--validation-dag-work', '200000000', '--track-resources', '--memory-mib', '2048',
            '--max-states', '2000000', '--outer-grace', '0', '--seconds', '5', '--repeat', '1',
            '--order-seed', str(plan['order_seed']), '--output', str(output)]
environment = dict(os.environ)
for key in ('VASS_PORTFOLIO_PROFILE', 'VASS_RELAXED_PROFILE'):
    environment.pop(key, None)
subprocess.run(command, cwd=ROOT, env=environment, check=True)
assert all(sha(Path(path)) == expected for path, expected in paths.items())
