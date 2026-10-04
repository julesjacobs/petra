#!/usr/bin/env python3
"""Reproduce local size and saved-timing evidence; never run a solver."""
import hashlib
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
sources = {}


def record(path):
    path = ROOT / path
    data = path.read_bytes()
    sources[str(path.relative_to(ROOT))] = hashlib.sha256(data).hexdigest()
    return data


def read(path):
    return json.loads(record(path))


ladder_path = Path('benchmarks/application-parameter-ladders-v2')
ladder = read(ladder_path / 'manifest.json')
instances = {}
for query in ladder['queries']:
    if query['instance'] in instances:
        continue
    item = dict(status=query['status'], places=query.get('places'), transitions=query.get('transitions'))
    if query['status'] == 'imported':
        pnml = ladder_path / query['pnml']
        item['pnml_bytes'] = (ROOT / pnml).stat().st_size
        item['manifest_pnml_sha256'] = query['pnml_sha256']
    instances[query['instance']] = item
fms = []
for query in ladder['queries']:
    if query['family'] == 'FMS' and query['property_slot'] == 0:
        path = ladder_path / query['branches'][0]['path']
        net = read(path)
        assert sources[str(path)] == query['branches'][0]['sha256']
        fms.append((query['instance'], net))
assert len(fms) == 11
assert all(net['places'] == fms[0][1]['places'] and net['transitions'] == fms[0][1]['transitions'] for _, net in fms)
varying_initial = [dict(index=i, place=fms[0][1]['places'][i], values=[net['initial'][i] for _, net in fms])
                   for i in range(len(fms[0][1]['places'])) if len({net['initial'][i] for _, net in fms}) > 1]
assert len(varying_initial) == 3
rows = [json.loads(line) for line in record('results/buffer-agglomeration-application-v1/runs.jsonl').splitlines()]
parse = {}
for method in ('control', 'buffer'):
    selected = [r for r in rows if r['method'] == method and 'rust_parse_seconds' in r]
    parse[method] = dict(rows_with_saved_parse=len(selected), rows_without_saved_parse=192-len(selected),
                         median_parse_seconds=statistics.median(r['rust_parse_seconds'] for r in selected),
                         maximum_parse_seconds=max(r['rust_parse_seconds'] for r in selected))
cohorts = [read('benchmarks/' + name + '/manifest.json') for name in ('diverse-ser-programs-v1', 'diverse-ser-scaling-v1')]
source_sets = [{case['sha256'] for case in cohort['cases']} for cohort in cohorts]
assert [len(cohort['cases']) for cohort in cohorts] == [12, 16]
assert len(source_sets[0] & source_sets[1]) == 4 and len(source_sets[0] | source_sets[1]) == 24
raw_rows = [json.loads(line) for line in record('results/raw-portfolio-component-after-v1/runs.jsonl').splitlines()]
raw_cases = {}
for row in raw_rows:
    if 'pairlocked' in row['query']:
        raw_cases.setdefault(row['query'], []).append({k:row.get(k) for k in ('repeat','verdict','status','stage','input','wall_seconds','independent_check','reason')})
for path in ('research/raw-component-game-portfolio-v1-analysis.json', 'research/raw-diverse-scaling-pilot-v1-analysis.json',
             'research/linux-hard-survivors-v1-verification.md', 'research/application-followups-v1-report.md',
             'research/raw-schemas-discovery.md', 'research/raw-negative-choice-progress.md',
             'research/harder-application-selection-v2.md', 'src/raw_negative.rs',
             'research/benchmark-hardness-next-track.md'):
    record(path)
record(Path(__file__).relative_to(ROOT))
report = dict(scope='Local read-only reproduction of metadata, canonical FMS structure and saved timing/result rows; no fresh proof checks or solver runs.',
              ladder_instances=instances,
              ladder_size_scope='PNML byte sizes read from existing files; identities quoted from manifest. This script hashes canonical FMS inputs but does not rehash all large PNML inputs.',
              fms=dict(instances=[name for name,_ in fms], identical_place_and_transition_structure=True, varying_initial_coordinates=varying_initial),
              application_saved_parse=parse,
              raw_source_cohorts=dict(sizes=[12,16], exact_sha256_bridge_count=4, unique_source_count=24),
              raw_pairlocked_saved_results=raw_cases,
              sources=sources)
output = ROOT / 'research/benchmark-hardness-next-track-evidence.json'
output.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(dict(output=str(output), fms_instances=len(fms), unique_raw_sources=24, application_saved_parse=parse), indent=2))
