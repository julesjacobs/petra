import argparse
import hashlib
import json
from pathlib import Path
import shlex
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from bounded_validation import run_validation
from process_runner import run, workspace_workloads

plan = json.loads((ROOT / 'research/capacity-regression-profile-v1-plan.json').read_text())
if workspace_workloads(ROOT):
    raise RuntimeError('Local workload is still active')
binary = ROOT / plan['binary']
if hashlib.sha256(binary.read_bytes()).hexdigest() != plan['binary_sha256']:
    raise ValueError('Frozen binary changed')
corpus = ROOT / 'benchmarks/mcc-stress-development'
query = next(q for q in json.loads((corpus / 'manifest.json').read_text())['queries']
             if q['name'] == plan['query'])
output = ROOT / 'results/capacity-regression-profile-v1'
output.mkdir(exist_ok=False)
args = argparse.Namespace(native_python=ROOT / 'vendor/venv/bin/python',
                          validation_memory_mib=2048, validation_response_mib=1,
                          validation_seconds=30)
with (output / 'runs.jsonl').open('w') as records:
    for repeat in range(3):
        for method in (['before', 'after'] if repeat % 2 == 0 else ['after', 'before']):
            prefix = output / f'{method}.{repeat}'
            profile = prefix.with_suffix(f'.{repeat}.profile.jsonl')
            log = prefix.with_suffix(f'.{repeat}.answer.json')
            wrapper = prefix.with_suffix(f'.{repeat}.sh')
            command = [str(binary), '--pnml', str(corpus / query['pnml']),
                       '--xml', str(corpus / query['xml']), '--property-id', query['property_id'],
                       '--method', 'portfolio-focused', '--seconds', '5']
            if method == 'before':
                command.append('--no-capacity-preprocessing')
            wrapper.write_text('VASS_PORTFOLIO_PROFILE=1 exec ' + shlex.join(command)
                               + ' 2>' + shlex.quote(str(profile)) + '\n')
            wall, code, expired, resources = run(['/bin/sh', str(wrapper)], ROOT, 5, log, 2048 * 1024**2)
            validation = run_validation(query, corpus, output, log, code, args,
                                        mode='rust-original-v1', outer_timeout=expired)
            row = dict(query=query['name'], method=method, repeat=repeat, wall_seconds=wall,
                       exit_code=code, outer_timeout=expired, resources=resources,
                       command=command, profile=str(profile), **validation)
            records.write(json.dumps(row) + '\n')
            records.flush()
            print(method, repeat, row['verdict'], flush=True)
