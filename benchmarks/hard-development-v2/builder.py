#!/usr/bin/env python3
"""Freeze a runnable view of jointly unresolved development queries."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path

from analyze_original_comparison import analyze, DEFINITIVE
from benchmark_smpt_classic import preflight_inputs

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    ('mcc-stress-development', 'linux-stress-relevance-v1'),
    ('boolean-consistency-v3', 'linux-dag-sat-v2'),
    ('fastforward-import-v2', 'linux-fastforward-shared-relevance-v1'),
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(output):
    records, evidence = [], []
    for corpus_name, result_name in SOURCES:
        corpus = ROOT / 'benchmarks' / corpus_name
        results = ROOT / 'results' / result_name
        paths = (corpus / 'manifest.json', results / 'environment.json', results / 'runs.jsonl')
        manifest, environment = [json.loads(p.read_text()) for p in paths[:2]]
        rows = [json.loads(line) for line in paths[2].read_text().splitlines()]
        if digest(paths[0]) != environment['manifest_sha256']:
            raise ValueError(f'Changed measured corpus: {corpus_name}')
        group_by = 'family' if all('family' in q for q in manifest['queries']) else 'suite'
        report = analyze(manifest, environment, rows, group_by=group_by)
        if set(environment['property_order']) != {q['name'] for q in manifest['queries']}:
            raise ValueError(f'Selection evidence must cover the full corpus: {corpus_name}')
        selected = {
            case['query'] for case in report['cases']
            if all(verdict not in DEFINITIVE
                   for verdicts in case['verdicts'].values() for verdict in verdicts)
        }
        selected_rows = [r for r in rows if r['query'] in selected]
        failures = [dict(query=r['query'], method=r['method'], verdict=r['verdict'],
                         capability_failures=r.get('capability_failures', []))
                    for r in selected_rows if r['verdict'] != 'unknown'
                    or r.get('capability_failures')]
        evidence.append(dict(
            corpus=corpus_name, full_denominator=report['properties'], selected=len(selected),
            sources={str(p.relative_to(ROOT)): digest(p) for p in paths},
            methods=environment['methods'], native_tools=environment.get('native_tools'),
            seconds=environment['seconds'], repeat=environment['repeat'],
            timeout_tracebacks=sum(bool(r.get('subprocess_error')) and bool(r.get('outer_timeout'))
                                   for r in selected_rows),
            failures=failures, cases=[c for c in report['cases'] if c['query'] in selected]))
        for original in manifest['queries']:
            if original['name'] not in selected:
                continue
            query = copy.deepcopy(original)
            query['development_source'] = str(paths[0].relative_to(ROOT))
            for key in ('pnml', 'xml', 'net', 'property', 'source_cnf'):
                if key in query:
                    query[key] = os.path.relpath(corpus / query[key], output)
            for branch in query['branches']:
                branch['path'] = os.path.relpath(corpus / branch['path'], output)
            records.append(query)
    if len({q['name'] for q in records}) != len(records):
        raise ValueError('Query names collide across source corpora')
    inputs = preflight_inputs(records, output, original=True)
    manifest = dict(
        format='smpt-classic-v1', expected_properties=len(records), queries=records,
        selection='All queries unresolved by every method and repetition in each complete source run.',
        scope='Outcome-selected development view. These are existing inputs, not additional independent '
              'benchmarks. Five-second unknowns are not established long-budget hardness or negative '
              'verdicts. Keep application and synthetic tracks separate, and retain full source denominators.',
        source_evidence=evidence, generator_sha256=digest(Path(__file__)),
        input_validation=dict(unique_files=len(inputs.seen), bytes_hashed=inputs.bytes_hashed),
        portability='Paths reference sibling frozen corpora; transfer the source corpora with this view.')
    output.mkdir(parents=True, exist_ok=False)
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (output / 'builder.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps(dict(properties=len(records), tracks=[
        dict(corpus=e['corpus'], properties=e['selected'], failures=len(e['failures'])) for e in evidence],
        manifest_sha256=digest(output / 'manifest.json'))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'benchmarks/hard-development-v2')
    build(parser.parse_args().output.resolve())
