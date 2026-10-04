#!/usr/bin/env python3
"""Combine an interrupted benchmark and its outcome-independent continuation."""
import argparse
import collections
import hashlib
import json
from pathlib import Path


def read_rows(path):
    return [json.loads(line) for line in (path/'runs.jsonl').read_text().splitlines()]


def combine(prior, continuation, manifest, output):
    provenance = json.loads((continuation/'SEGMENT.json').read_text())
    previous = json.loads((prior/'environment.json').read_text())
    current = json.loads((continuation/'environment.json').read_text())
    if hashlib.sha256((prior/'runs.jsonl').read_bytes()).hexdigest() != provenance['prior_records_sha256']:
        raise ValueError('Prior records changed')
    if previous['manifest_sha256'] != hashlib.sha256(manifest.read_bytes()).hexdigest():
        raise ValueError('Manifest changed')
    for field in ('seconds', 'repeat', 'methods', 'max_states', 'platform',
                  'manifest_sha256', 'binary_sha256', 'baseline_binary_sha256',
                  'scope', 'smpt_configurations', 'smpt_root', 'smpt_python',
                  'auto_reduce', 'track_resources', 'smpt_original', 'outer_grace',
                  'memory_mib', 'tools', 'smpt_source_sha256'):
        if previous[field] != current[field]:
            raise ValueError(f'Incompatible configuration: {field}')
    methods = previous['methods']
    expected = {(method, repeat) for method in methods for repeat in range(previous['repeat'])}
    first, second = read_rows(prior), read_rows(continuation)
    groups = collections.defaultdict(set)
    for record in first:
        key = (record['method'], record['repeat'])
        if key in groups[record['query']]:
            raise ValueError('Duplicate prior record')
        groups[record['query']].add(key)
    complete = {query for query, observed in groups.items() if observed == expected}
    if complete != set(provenance['retained_complete_properties']):
        raise ValueError('Continuation does not retain all complete prior properties')
    queries = {q['name']: q for q in json.loads(manifest.read_text())['queries']}
    remaining = set(queries) - complete
    if remaining != set(provenance['rerun_properties']):
        raise ValueError('Continuation selection is incomplete')
    rows = [dict(r, segment=str(prior)) for r in first if r['query'] in complete]
    rows += [dict(r, segment=str(continuation)) for r in second]
    observed = set()
    for record in rows:
        key = (record['query'], record['method'], record['repeat'])
        if key in observed:
            raise ValueError('Duplicate combined record')
        observed.add(key)
        if record['query'] not in queries or (record['method'], record['repeat']) not in expected:
            raise ValueError('Unexpected combined record')
        if record['segment'] == str(continuation) and record['query'] not in remaining:
            raise ValueError('Continuation reran a retained property')
    if observed != {(query, method, repeat) for query in queries for method, repeat in expected}:
        raise ValueError('Benchmark segments are not complete')
    if output.exists():
        raise ValueError('Output already exists')
    output.mkdir(parents=True)
    (output/'runs.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    (output/'environment.json').write_text(json.dumps(dict(
        segments=[str(prior), str(continuation)], configurations=[previous, current],
        continuation=provenance,
        caveat='One exploratory shared-host pass, completed in two segments after a macOS cleanup API error. No fastest-run selection; every complete prior property retained regardless of outcome.'), indent=2)+'\n')
    lines = ['# Development comparison', '',
             f'{len(queries)} original properties; {previous["seconds"]}s common outer deadline; {previous["repeat"]} repetition(s).', '',
             '| Method | Reachable | Unreachable | Unknown | Error/unstable |', '|---|---:|---:|---:|---:|']
    definitive = {}
    for method in methods:
        per_query = collections.defaultdict(set)
        for r in rows:
            if r['method'] == method:
                per_query[r['query']].add(r['verdict'])
        outcomes = {q: next(iter(v)) if len(v) == 1 else 'unstable' for q,v in per_query.items()}
        counts = collections.Counter(outcomes.values())
        lines.append(f'| {method} | {counts["reachable"]} | {counts["unreachable"]} | {counts["unknown"]} | {sum(v for k,v in counts.items() if k not in ("reachable","unreachable","unknown"))} |')
        definitive[method] = {q for q,v in outcomes.items() if v in ('reachable','unreachable')}
    disagreements = []
    for query in queries:
        truths = {r['property_truth'] for r in rows if r['query'] == query and r['property_truth'] is not None}
        if len(truths) > 1:
            disagreements.append(query)
    lines += ['', f'Definitive disagreements: {disagreements}.', '',
              'Every complete property in the interrupted segment was retained regardless of outcome. Incomplete and unvisited properties were rerun in full. The only execution-path runner change catches a macOS process-environment API error during cleanup. Source snapshots and segment provenance remain available.', '',
              'Native per-branch verification status is recorded in runs.jsonl. External SMPT proofs were not independently checked. SMPT uses the documented portable plain-WALK compatibility patch with automatic reduction. This is one shared-host exploratory pass, not publication-grade timing.', '',
              'Input-cost boundary: native solvers received pretranslated JSON branches, while SMPT received original PNML/XML with parsing and reduction inside timing. This run does not establish matched original-input end-to-end superiority.']
    if 'portfolio-causal' in definitive and 'frozen-v2' in definitive:
        gains = definitive['portfolio-causal'] - definitive['frozen-v2']
        losses = definitive['frozen-v2'] - definitive['portfolio-causal']
        lines += ['', f'Causal portfolio vs frozen v2: {len(gains)} additional solves, {len(losses)} lost solves.', '',
                  '| Family | Additional solves | Lost solves |', '|---|---:|---:|']
        for family in sorted({q['family'] for q in queries.values()}):
            lines.append(f'| {family} | {sum(queries[q]["family"] == family for q in gains)} | {sum(queries[q]["family"] == family for q in losses)} |')
    failures = [r for r in rows if r.get('capability_failures')]
    lines += ['', f'Runs with dependency/interface failures: {len(failures)}.']
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n')
    return not disagreements and not any(r['verdict'] == 'error' for r in rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prior', type=Path)
    parser.add_argument('continuation', type=Path)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    raise SystemExit(0 if combine(args.prior, args.continuation, args.manifest, args.output) else 1)


if __name__ == '__main__':
    main()
