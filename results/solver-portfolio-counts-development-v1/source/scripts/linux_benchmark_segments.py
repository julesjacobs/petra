#!/usr/bin/env python3
"""Strict continuation and combination for the original-input Linux comparison."""
import argparse
from collections import defaultdict
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rows(path):
    return [json.loads(line) for line in (path / 'runs.jsonl').read_text().splitlines()]


def schedule(environment, selected=None):
    for index, query in enumerate(environment['property_order']):
        if selected is not None and query not in selected:
            continue
        for repeat in range(environment['repeat']):
            order = environment['methods'] if repeat % 2 == 0 else environment['methods'][::-1]
            if environment['order_seed'] is not None:
                offset = (index + repeat) % len(order)
                order = order[offset:] + order[:offset]
            for method in order:
                yield query, method, repeat


def key(row):
    return row['query'], row['method'], row['repeat']


def selection(previous, first):
    expected = list(schedule(previous))
    if [key(row) for row in first] != expected[:len(first)]:
        raise ValueError('Prior records are not a unique prefix of the recorded full schedule')
    groups = defaultdict(set)
    for row in first:
        groups[row['query']].add((row['method'], row['repeat']))
    pairs = {(method, repeat) for method in previous['methods'] for repeat in range(previous['repeat'])}
    complete = {query for query, observed in groups.items() if observed == pairs}
    remaining = set(previous['property_order']) - complete
    return complete, remaining


def check_runner_patch(old, new):
    before = old.read_text()
    expected = before.replace('import csv\n', 'import csv\nimport errno\n', 1).replace(
        '    except FileNotFoundError:\n        return\n',
        '    except OSError as error:\n        if error.errno in (errno.ENOENT, errno.ENODEV):\n            return\n        raise\n', 1)
    if expected == before or expected != new.read_text():
        raise ValueError('Runner change exceeds the recorded ENOENT/ENODEV race fix')


def verify_snapshots(directory, environment):
    for name, expected in environment['script_sha256'].items():
        if digest(directory / 'runner-source' / name) != expected:
            raise ValueError(f'Snapshot hash mismatch: {name}')


def compare_configuration(previous, current):
    ignored = {'queries', 'property_order', 'script_sha256', 'linux_host', 'continuation'}
    if set(previous) - ignored != set(current) - ignored:
        raise ValueError('Configuration fields changed')
    for field in set(previous) - ignored:
        if previous[field] != current[field]:
            raise ValueError(f'Incompatible configuration: {field}')
    for field in ('topology', 'kernel', 'perf_event_paranoid'):
        if previous['linux_host'][field] != current['linux_host'][field]:
            raise ValueError(f'Linux host changed: {field}')
    for field in set(previous['script_sha256']) | set(current['script_sha256']):
        if field != 'linux_runner.py' and previous['script_sha256'].get(field) != current['script_sha256'].get(field):
            raise ValueError(f'Script changed: {field}')


def resume(prior, corpus, output, binary, baseline, prepare_only=False):
    import benchmark_smpt_classic as harness
    previous = json.loads((prior / 'environment.json').read_text())
    first = rows(prior)
    complete, remaining = selection(previous, first)
    manifest = corpus / 'manifest.json'
    if digest(manifest) != previous['manifest_sha256']:
        raise ValueError('Manifest changed')
    queries = {q['name']: q for q in json.loads(manifest.read_text())['queries']}
    if set(queries) != set(previous['property_order']):
        raise ValueError('Full property order does not match manifest')
    if previous['linux_cpus'] != [8] or not previous['perf'] or not previous['native_original'] or not previous['smpt_original']:
        raise ValueError('This continuation requires the recorded single-core original-input perf track')
    verify_snapshots(prior, previous)
    check_runner_patch(prior / 'runner-source/linux_runner.py', harness.ROOT / 'scripts/linux_runner.py')
    current = copy.deepcopy(previous)
    for name, old_hash in previous['script_sha256'].items():
        actual = digest(harness.ROOT / 'scripts' / name)
        if name != 'linux_runner.py' and actual != old_hash:
            raise ValueError(f'Frozen harness dependency changed: {name}')
        current['script_sha256'][name] = actual
    for path, expected in [(binary, previous['binary_sha256']), (baseline, previous['baseline_binary_sha256']),
                           (previous['native_python'], previous['native_python_sha256']),
                           (previous['verifypn']['binary'], previous['verifypn']['binary_sha256'])]:
        if digest(path) != expected:
            raise ValueError(f'Executable changed: {path}')
    for name, item in previous['tools'].items():
        if digest(item['path']) != item['sha256']:
            raise ValueError(f'Tool changed: {name}')
    for name, expected in previous['smpt_source_sha256'].items():
        if digest(Path(previous['smpt_root']) / name) != expected:
            raise ValueError(f'SMPT source changed: {name}')
    for q in queries.values():
        for path_key, hash_key in [('pnml', 'pnml_sha256'), ('xml', 'xml_sha256'), ('net', 'net_sha256'), ('property', 'property_sha256')]:
            harness.checked(corpus / q[path_key], q[hash_key])
        for branch in q['branches']:
            harness.checked(corpus / branch['path'], branch['sha256'])
    current['linux_host'].update(
        lscpu=subprocess.check_output(['lscpu'], text=True),
        topology=subprocess.check_output(['lscpu', '-e=CPU,CORE,CACHE'], text=True),
        kernel=os.uname().release,
        perf_event_paranoid=Path('/proc/sys/kernel/perf_event_paranoid').read_text().strip(),
        loadavg=Path('/proc/loadavg').read_text().strip())
    compare_configuration(previous, current)
    provenance = dict(prior=str(prior), prior_records_sha256=digest(prior / 'runs.jsonl'),
                      prior_environment_sha256=digest(prior / 'environment.json'),
                      retained_complete_properties=sorted(complete), rerun_properties=sorted(remaining),
                      full_property_order=previous['property_order'],
                      schedule='Original full-property indices and method rotations preserved; incomplete properties rerun in full.',
                      runner_change='Only catch ENODEV alongside ENOENT when cgroup.procs disappears.',
                      continuation_script_sha256=digest(__file__))
    current.update(queries=len(remaining), property_order=[q for q in previous['property_order'] if q in remaining],
                   continuation=provenance)
    if output.exists():
        raise ValueError('Continuation output already exists')
    if prepare_only:
        print(json.dumps(dict(complete=len(complete), remaining=len(remaining), invocations=len(list(schedule(previous, remaining))), provenance=provenance), indent=2))
        return
    output.mkdir(parents=True)
    (output / 'SEGMENT.json').write_text(json.dumps(provenance, indent=2) + '\n')
    (output / 'environment.json').write_text(json.dumps(current, indent=2) + '\n')
    snapshot = output / 'runner-source'
    snapshot.mkdir()
    for name in current['script_sha256']:
        shutil.copyfile(harness.ROOT / 'scripts' / name, snapshot / name)
    shutil.copyfile(__file__, snapshot / Path(__file__).name)
    tool_dirs = list(dict.fromkeys(str(Path(item['path']).parent) for item in previous['tools'].values()))
    os.environ['PATH'] = os.pathsep.join([str(harness.ROOT / 'vendor/venv/bin'), *tool_dirs, os.environ['PATH']])
    args = SimpleNamespace(**previous)
    for field in ('smpt_root', 'smpt_python', 'native_python'):
        setattr(args, field, Path(getattr(args, field)))
    args.binary, args.baseline_binary = binary, baseline
    args.verifypn_binary = Path(previous['verifypn']['binary'])
    args.verifypn_root = Path(previous['verifypn']['source'])
    with (output / 'runs.jsonl').open('w') as stream:
        for query_name, method, repeat in schedule(previous, remaining):
            query = queries[query_name]
            if method == 'verifypn':
                from verifypn_runner import run
                result = run(query, corpus, output, method, repeat, args, harness.execute)
            else:
                run = harness.smpt if method in harness.SMPT_MODES else harness.native
                result = run(query, corpus, output, method, repeat, args)
            row = dict(query=query_name, suite=query['suite'], method=method, repeat=repeat,
                       property_kind=query.get('kind'), **result)
            row['property_truth'] = harness.property_truth(query.get('kind'), row['verdict'])
            stream.write(json.dumps(row) + '\n')
            stream.flush()
            print(query_name, method, repeat, row['verdict'], row['property_truth'], flush=True)


def combine(prior, continuation, manifest, output):
    previous = json.loads((prior / 'environment.json').read_text())
    current = json.loads((continuation / 'environment.json').read_text())
    provenance = json.loads((continuation / 'SEGMENT.json').read_text())
    if current['continuation'] != provenance:
        raise ValueError('Provenance mismatch')
    if digest(prior / 'runs.jsonl') != provenance['prior_records_sha256'] or digest(prior / 'environment.json') != provenance['prior_environment_sha256']:
        raise ValueError('Prior segment changed')
    if digest(manifest) != previous['manifest_sha256']:
        raise ValueError('Manifest changed')
    compare_configuration(previous, current)
    verify_snapshots(prior, previous)
    verify_snapshots(continuation, current)
    check_runner_patch(prior / 'runner-source/linux_runner.py', continuation / 'runner-source/linux_runner.py')
    if digest(continuation / 'runner-source/linux_benchmark_segments.py') != provenance['continuation_script_sha256']:
        raise ValueError('Continuation driver changed')
    first, second = rows(prior), rows(continuation)
    complete, remaining = selection(previous, first)
    if complete != set(provenance['retained_complete_properties']) or remaining != set(provenance['rerun_properties']):
        raise ValueError('Selection is not outcome-independent complete-group retention')
    if provenance['full_property_order'] != previous['property_order']:
        raise ValueError('Full ordering changed')
    if current['queries'] != len(remaining) or current['property_order'] != [q for q in previous['property_order'] if q in remaining]:
        raise ValueError('Continuation property order changed')
    if [key(row) for row in second] != list(schedule(previous, remaining)):
        raise ValueError('Continuation incomplete or method rotation changed')
    combined = [dict(row, segment=str(prior)) for row in first if row['query'] in complete]
    combined += [dict(row, segment=str(continuation)) for row in second]
    if [key(row) for row in combined] != list(schedule(previous)):
        raise ValueError('Combined schedule incomplete')
    if output.exists():
        raise ValueError('Output already exists')
    output.mkdir(parents=True)
    environment = copy.deepcopy(previous)
    environment['segments'] = [str(prior), str(continuation)]
    environment['segment_configurations'] = [previous, current]
    environment['segment_provenance'] = provenance
    environment['continuation_caveat'] = 'Complete properties retained regardless of outcome; partial/unvisited properties rerun. Cgroup disappearance race fixed; original method rotations preserved.'
    (output / 'environment.json').write_text(json.dumps(environment, indent=2) + '\n')
    (output / 'runs.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in combined))
    return len(combined)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    resume_parser = sub.add_parser('resume')
    combine_parser = sub.add_parser('combine')
    for p in (resume_parser, combine_parser):
        p.add_argument('--prior', type=Path, required=True)
        p.add_argument('--output', type=Path, required=True)
    resume_parser.add_argument('--corpus', type=Path, required=True)
    resume_parser.add_argument('--binary', type=Path, required=True)
    resume_parser.add_argument('--baseline', type=Path, required=True)
    resume_parser.add_argument('--prepare-only', action='store_true')
    combine_parser.add_argument('--continuation', type=Path, required=True)
    combine_parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    values = {k: v.resolve() if isinstance(v, Path) else v for k, v in vars(args).items() if k != 'action'}
    if args.action == 'resume':
        resume(**values)
    else:
        print(combine(**values))


if __name__ == '__main__':
    main()
