"""Recheck three preserved proposed negatives; this does not rerun the solver."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from bounded_validation import run_validation

output = ROOT / 'results/dag-proof-recheck-v3'
output.mkdir(exist_ok=False)
snapshot = output / 'runner-source'
snapshot.mkdir()
for script in (ROOT / 'scripts').glob('*.py'):
    shutil.copyfile(script, snapshot / script.name)
args = SimpleNamespace(native_python=ROOT / 'vendor/venv/bin/python', validation_seconds=30,
                       validation_memory_mib=2048, validation_response_mib=16,
                       validation_dag_work=200_000_000)
rows = []
source = ROOT / 'results/dag-limits-diagnostic-v2'
names = ['random3_n72_r480_s2026092702', 'random3_n96_r426_s2026092702',
         'random3_n96_r480_s2026092701']
for name in names:
    logname = name + '.dag-large.0.rust-original.json'
    request = json.loads((source / (logname + '.validation-request.json')).read_text())
    copied = output / logname
    shutil.copyfile(source / logname, copied)
    result = run_validation(request['query'], Path(request['corpus']), output, copied,
                            request['exit_code'], args, mode='rust-original-v1')
    row = dict(query=name, source_log=str((source/logname).relative_to(ROOT)),
               proof_output_sha256=hashlib.sha256(copied.read_bytes()).hexdigest(), **result)
    rows.append(row)
    (output / 'runs.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    print(name, result['verdict'], result.get('validation_failure'), flush=True)
(output / 'environment.json').write_text(json.dumps(dict(
    scope='Post-hoc higher-budget independent checking of preserved solver outputs; not a new solver comparison.',
    seconds=30, dag_work=200_000_000, response_mib=16, memory_mib=2048,
    memory_caveat='Portable sampled process-tree RSS on Mac; not an enforced cgroup limit.',
    sources={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in snapshot.glob('*.py')}
), indent=2)+'\n')
