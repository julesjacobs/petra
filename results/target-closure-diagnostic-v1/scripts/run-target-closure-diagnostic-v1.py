import argparse
import hashlib
import json
from pathlib import Path
import random
import shlex
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from bounded_validation import InputChecks, run_validation
from process_runner import run, workspace_workloads

plan_path = ROOT / 'research/target-closure-diagnostic-v1-plan.json'
plan = json.loads(plan_path.read_text())
if workspace_workloads(ROOT):
    raise RuntimeError('Local workload is still active')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

binaries = {method: ROOT / spec['path'] for method, spec in plan['binaries'].items()}
corpus = ROOT / plan['corpus']
for method, binary in binaries.items():
    assert digest(binary) == plan['binaries'][method]['sha256']
    assert digest(binary.parent / 'source.tar.gz') == plan['source_sha256'][method]
assert digest(corpus / 'manifest.json') == plan['manifest_sha256']
queries = {q['name']: q for q in json.loads((corpus / 'manifest.json').read_text())['queries']}
assert len(set(plan['queries'])) == plan['properties']
checks = InputChecks()
for name in plan['queries']:
    query = queries[name]
    for key in ['pnml', 'xml']:
        checks.check(corpus / query[key], query[key + '_sha256'])
    for branch in query['branches']:
        checks.check(corpus / branch['path'], branch['sha256'])

output = ROOT / plan['output']
output.mkdir(exist_ok=False)
shutil.copyfile(plan_path, output / 'plan.json')
snapshot = output / 'scripts'
snapshot.mkdir()
screen_env = json.loads((ROOT / 'results/target-closure-screen-v1/environment.json').read_text())
runner_hashes = {}
for name, expected in screen_env['script_sha256'].items():
    path = ROOT / 'scripts' / name
    if not path.exists():
        path = ROOT / name
    assert digest(path) == expected, name
    shutil.copyfile(path, snapshot / name)
    runner_hashes[name] = expected
shutil.copyfile(__file__, snapshot / Path(__file__).name)
runner_hashes[Path(__file__).name] = digest(Path(__file__))
args = argparse.Namespace(native_python=ROOT / 'vendor/venv/bin/python',
                          validation_memory_mib=plan['validation']['memory_mib'],
                          validation_response_mib=plan['validation']['response_mib'],
                          validation_seconds=plan['validation']['seconds'],
                          validation_dag_work=plan['validation']['dag_max_work'])
rng = random.Random(plan['order_seed'])
order = list(plan['queries'])
rng.shuffle(order)
(output / 'environment.json').write_text(json.dumps(dict(
    plan=plan, query_order=order, runner_sha256=runner_hashes,
    input_files_hashed=len(checks.seen), input_bytes_hashed=checks.bytes_hashed), indent=2) + '\n')
completed = 0
with (output / 'runs.jsonl').open('w') as records:
    for name in order:
        query = queries[name]
        methods = list(plan['methods'])
        rng.shuffle(methods)
        for method in methods:
            binary = binaries[method]
            stem = f'{name}.{method}.0'
            profile = output / (stem + '.profile.jsonl')
            answer = output / (stem + '.rust-original.json')
            wrapper = output / (stem + '.sh')
            command = [str(binary), '--pnml', str(corpus / query['pnml']),
                       '--xml', str(corpus / query['xml']), '--property-id', query['property_id'],
                       '--method', plan['methods'][method], '--seconds', str(plan['seconds']),
                       '--max-states', str(plan['max_states'])]
            wrapper.write_text('VASS_PORTFOLIO_PROFILE=1 VASS_RELAXED_PROFILE=1 exec '
                               + shlex.join(command) + ' 2>' + shlex.quote(str(profile)) + '\n')
            wall, code, expired, resources = run(['/bin/sh', str(wrapper)], ROOT,
                                                 plan['outer_seconds'], answer,
                                                 plan['memory_mib'] * 1024**2)
            validation = run_validation(query, corpus, output, answer, code, args,
                                        mode='rust-original-v1', outer_timeout=expired)
            events, other_lines = [], []
            for line in profile.read_text().splitlines():
                try:
                    event = json.loads(line)
                except ValueError:
                    other_lines.append(line)
                else:
                    events.append(event)
            row = dict(query=name, method=method, repeat=0, wall_seconds=wall,
                       exit_code=code, outer_timeout=expired, resources=resources,
                       command=command, profile=str(profile), answer=str(answer),
                       events=events, other_profile_lines=other_lines,
                       input_mode='rust-original-v1', **validation)
            records.write(json.dumps(row) + '\n')
            records.flush()
            completed += 1
            print(name, method, row['verdict'], len(events), flush=True)
checks.unchanged()
assert completed == plan['expected_rows']
(output / 'completed.json').write_text(json.dumps(dict(rows=completed, all_inputs_unchanged=True)) + '\n')
