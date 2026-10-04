"""Freeze inputs, binaries, runtime identities and the complete two-block schedule."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import sys

F = Path(__file__).resolve().parent
ROOT = F.parents[1]
REMOTE = Path('/home/jules/experiments/pvass-publication')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    assert sys.platform == 'linux' and ROOT == REMOTE
    assert not (F / 'plan.json').exists()
    sys.path.insert(0, str(F / 'runner-source/scripts'))
    from process_runner import workspace_workloads
    assert not workspace_workloads(ROOT)
    build = json.loads((F / 'build-receipt-v2.json').read_text())
    assert build['exit_code'] == 0 and build['tests']['exit_code'] == 0
    assert sha(F / 'candidate-vass-reach') == build['binary_sha256']
    config = json.loads((F / 'freeze-config.json').read_text())
    qualification = json.loads((ROOT / config['its_qualification']).read_text())
    assert qualification['status'] == 'passed', 'ITS runtime qualification must pass'
    protocol = json.loads((F / 'protocol.json').read_text())
    old = json.loads((ROOT / 'research/repeated-comparison-linux-v1/b1-5s/plan.json').read_text())
    pins = json.loads((F / 'input-sha256.json').read_text())
    pins.update(json.loads((F / 'inherited-runtime-sha256.json').read_text()))
    for name, digest in json.loads((F / 'analysis-sha256.json').read_text()).items():
        path = ROOT / name
        assert sha(path) == digest, name
        pins[name] = digest
    pins[str((F / 'analysis-sha256.json').relative_to(ROOT))] = sha(F / 'analysis-sha256.json')
    for name, digest in json.loads((F / 'candidate-source-sha256.json').read_text()).items():
        pins[str((F / 'candidate-source' / name).relative_to(ROOT))] = digest
    for path in (F / 'runner-source/scripts').glob('*'):
        if path.is_file():
            pins[str(path.relative_to(ROOT))] = sha(path)
    for name in ['protocol.json', 'candidate-source-sha256.json', 'candidate-source-provenance.json',
                 'candidate-vass-reach', 'build-receipt.json', 'build-receipt-v2.json',
                 'test-fixtures-sha256.json', 'test-retry.py', 'run.py', 'capability.py', 'freeze.py', 'freeze-config.json']:
        pins[str((F / name).relative_to(ROOT))] = sha(F / name)
    pins.update(config['its_file_sha256'])
    pins[config['its_qualification']] = sha(ROOT / config['its_qualification'])
    external = config.get('external_file_sha256', {})
    for name, digest in pins.items():
        assert sha(ROOT / name) == digest, name
    for name, digest in external.items():
        assert Path(name).is_absolute() and sha(Path(name)) == digest, name
    plan = dict(format='competitive-linux-20261004-v1', frozen_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                protocol=protocol, protocol_sha256=sha(F / 'protocol.json'), properties=368,
                representatives=366, expected_rows=2944, seconds=5, repeat=2,
                methods=['native-excess', 'verifypn-default', 'smpt-mcc-portable', 'its-mcc'],
                corpus='benchmarks/competitive-development-v5',
                manifest_sha256=sha(ROOT / 'benchmarks/competitive-development-v5/manifest.json'),
                candidate_binary=str((F / 'candidate-vass-reach').relative_to(ROOT)),
                candidate_binary_sha256=build['binary_sha256'],
                candidate_source_manifest_sha256=sha(F / 'candidate-source-sha256.json'),
                runner_source=str((F / 'runner-source').relative_to(ROOT)),
                linux_cpus=[8], memory_mib=2048, perf=True, max_states=2000000, outer_grace=0,
                validation=old['validation'], verifypn=old['verifypn'],
                smpt_configurations=old['smpt_configurations'], smpt_scheduling=old['smpt_scheduling'],
                minizinc_preflight=old['minizinc_preflight'], minizinc_tool_bin=old['minizinc_tool_bin'],
                its_harness_options=config['its_harness_options'], its_qualification=config['its_qualification'],
                its_runtime=config['its_runtime'], required_file_sha256=pins, external_file_sha256=external,
                blocks=[])
    spec = importlib.util.spec_from_file_location('campaign_run', F / 'run.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    queries = json.loads((ROOT / plan['corpus'] / 'manifest.json').read_text())['queries']
    for index, seed in enumerate([2026100405, 2026100406]):
        name = f'repeat{index + 1}'
        methods = plan['methods'] if index == 0 else plan['methods'][::-1]
        shuffled = list(queries)
        random.Random(seed).shuffle(shuffled)
        schedule = []
        for qi, query in enumerate(shuffled):
            offset = qi % 4
            schedule.extend(dict(query=query['name'], method=method, repeat=0,
                                 source_corpus=query['source_corpus']) for method in methods[offset:] + methods[:offset])
        block = dict(name=name, methods=methods, order_seed=seed, output=f'results/competitive-linux-20261004/{name}',
                     expected_rows=1472, property_order=[q['name'] for q in shuffled], schedule=schedule)
        block['command'] = runner.command(plan, block)
        plan['blocks'].append(block)
    with (F / 'plan.json').open('x') as out:
        json.dump(plan, out, indent=2)
        out.write('\n')
    print(json.dumps(dict(status='frozen', plan_sha256=sha(F / 'plan.json'),
                         pins=len(pins), external_pins=len(external), rows=2944)), flush=True)


if __name__ == '__main__':
    main()
