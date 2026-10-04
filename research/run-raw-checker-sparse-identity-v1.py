"""Register matched checks of the same saved proof; no solver or remote operation."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from process_runner import run, workspace_workloads

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

assert not workspace_workloads(ROOT)
output = ROOT / 'results/raw-checker-sparse-identity-v1'
output.mkdir()
snapshot = output / 'runner-source'
snapshot.mkdir()
files = ['raw_stress_worker.py', 'raw_invariant_check.py', 'raw_schema_check.py',
         'raw_automaton_check.py', 'raw_z3.py', 'process_runner.py',
         'test_raw_invariant_check.py', 'test_raw_schema_check.py']
for name in files:
    shutil.copy2(ROOT / 'scripts' / name, snapshot / name)
worker = output / 'check-saved-raw-proof-v1.py'
shutil.copy2(ROOT / 'research/check-saved-raw-proof-v1.py', worker)
source = ROOT / 'results/raw-proof-streaming-pilot-v1-streamed'
query = source / 'inputs/write_skew_n5_pairlocked.json'
answer = source / 'write_skew_n5_pairlocked.raw-negative.0/solver.stdout'
old = source / 'runner-source'
identities = {str(p.relative_to(ROOT)): sha(p) for p in
              [query, answer, worker, Path(__file__).resolve(),
               ROOT / 'research/raw-checker-sparse-identity-tests.log',
               *snapshot.glob('*.py'), *old.glob('*.py')]}
runs = []
for label, checker in [('dense', old), ('sparse', snapshot)]:
    command = [sys.executable, str(worker), '--checker-dir', str(checker),
               '--query', str(query), '--answer', str(answer), '--seconds', '120',
               '--work', '10000000000']
    runs.append(dict(label=label, command=command))
plan = dict(scope='Independent-checker memory ablation on the same saved proof. 120s input/check-inclusive and sampled2GiB per row,10Bwork. Solver and proof generation excluded; not an end-to-end solve or timing claim. Acceptance rules unchanged; duplicate-node keys become exact sparse vectors after full validation.',
            runs=runs, file_sha256=identities, seconds=120, memory_bytes=2 * 1024**3)
(ROOT / 'research/raw-checker-sparse-identity-v1-plan.json').write_text(json.dumps(plan, indent=2) + '\n')
rows = []
for item in runs:
    assert all(sha(ROOT / name) == digest for name, digest in identities.items())
    log = output / (item['label'] + '.log')
    wall, code, expired, usage = run(item['command'], ROOT, 120, log, memory_bytes=2 * 1024**3)
    records = [json.loads(line) for line in log.read_text().splitlines() if line.startswith('{')]
    accepted = (code == 0 and not expired and not usage['memory_limit_exceeded']
                and records and records[-1].get('accepted') is True
                and records[-1].get('checker') == 'python-raw-automaton-invariant')
    row = dict(label=item['label'], command=item['command'], accepted=bool(accepted),
               wall_seconds=wall, exit_code=code, outer_timeout=expired, usage=usage,
               records=records, log_sha256=sha(log))
    rows.append(row)
    (ROOT / 'research/raw-checker-sparse-identity-v1-results.json').write_text(json.dumps(rows, indent=2) + '\n')
    print(json.dumps(row), flush=True)
