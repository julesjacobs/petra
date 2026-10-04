#!/usr/bin/env python3
"""Freeze every jointly unresolved query in the complete hard-development-v2 run."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path

from analyze_original_comparison import analyze, DEFINITIVE

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / 'benchmarks/hard-development-v2'
RESULTS = ROOT / 'results/linux-hard-development-v2'
METHODS = ['native-focused', 'native-symbolic', 'verifypn-default', 'smpt-full-portable']
NATIVE_SHA256 = 'e3e7f057d8885b82238a0c86a50ef56fc5492946aa85eaabc805387b609dc37a'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')


def build(output):
    paths = [CORPUS / 'manifest.json', RESULTS / 'environment.json', RESULTS / 'runs.jsonl']
    manifest, environment = [json.loads(p.read_text()) for p in paths[:2]]
    rows = [json.loads(line) for line in paths[2].read_text().splitlines()]
    queries = {q['name']: q for q in manifest['queries']}
    if (len(queries) != 69 or len(manifest['queries']) != 69 or len(rows) != 276
            or environment['methods'] != METHODS or environment['repeat'] != 1
            or set(environment['property_order']) != set(queries)
            or environment['manifest_sha256'] != digest(paths[0])
            or environment['binary_sha256'] != NATIVE_SHA256):
        raise ValueError('Unexpected or changed complete selection run')
    report = analyze(manifest, environment, rows, group_by='suite')
    matrix = {(r['query'], r['method']): r for r in rows}
    selected = sorted(n for n in queries if all(
        matrix[n, m]['verdict'] not in DEFINITIVE for m in METHODS))
    if len(selected) != 8:
        raise ValueError(f'Expected eight survivors, obtained {len(selected)}')
    reserved_path = ROOT / 'benchmarks/reserved-evaluation-v2.json'
    reserved = set(json.loads(reserved_path.read_text())['reserved_families'])
    if any(q.get('family') in reserved or q.get('family_group') in reserved
           for q in queries.values()):
        raise ValueError('Reserved family in development source')
    parent_evidence = copy.deepcopy(manifest['source_evidence'])
    if sum(e['full_denominator'] for e in parent_evidence) != 620:
        raise ValueError('Changed parent denominator')
    for evidence in parent_evidence:
        for filename, expected in evidence['sources'].items():
            if digest(ROOT / filename) != expected:
                raise ValueError(f'Changed parent evidence: {filename}')

    identities = {}

    def checked(path, expected):
        path = path.resolve()
        key = str(path.relative_to(ROOT))
        if key not in identities:
            identities[key] = dict(sha256=digest(path), bytes=path.stat().st_size)
        if identities[key]['sha256'] != expected:
            raise ValueError(f'Changed input: {key}')
        return path

    # Check the entire measured input set, not only retained rows.
    records = []
    for name in sorted(queries):
        original = queries[name]
        query = copy.deepcopy(original)
        for key in ('pnml', 'xml', 'net', 'property', 'source_cnf'):
            if key in query:
                path = checked(CORPUS / query[key], query[key + '_sha256'])
                query[key] = os.path.relpath(path, output)
        for branch in query['branches']:
            path = checked(CORPUS / branch['path'], branch['sha256'])
            branch['path'] = os.path.relpath(path, output)
        if 'source_mapping' in query:
            source = ROOT / query['development_source']
            path = checked(source.parent / query['source_mapping'], query['source_mapping_sha256'])
            query['source_mapping'] = os.path.relpath(path, output)
        for key in ('source_lola', 'source_formula'):
            if key in query:
                path = checked(ROOT / 'benchmarks/fastforward-repository-v1/upstream' / query[key],
                               query[key + '_sha256'])
                query[key + '_local'] = os.path.relpath(path, output)
        if name in selected:
            query['selection_source'] = str(paths[0].relative_to(ROOT))
            records.append(query)
    decisions = []
    for name in sorted(queries):
        definitive = [m for m in METHODS if matrix[name, m]['verdict'] in DEFINITIVE]
        decisions.append(dict(query=name, selected=name in selected,
                              definitive_methods=definitive,
                              verdicts={m: matrix[name, m]['verdict'] for m in METHODS}))
    if any(d['selected'] != (not d['definitive_methods']) for d in decisions):
        raise ValueError('Selection omitted an unresolved query')
    audit = dict(
        format='hard-survivors-selection-v1', full_properties=69, full_rows=276,
        parent_properties=620, selected_properties=len(records), union_solved=69-len(records),
        sources={str(p.relative_to(ROOT)): digest(p) for p in paths},
        reserved_manifest_sha256=digest(reserved_path), reserved_overlap=[],
        parent_evidence=parent_evidence, decisions=decisions,
        full_matrix=rows, input_identities=identities,
        input_validation=dict(unique_files=len(identities),
                              bytes_hashed=sum(v['bytes'] for v in identities.values())),
        counts=report['counts'], suites=report['suites'],
        completeness='All 69 queries have exactly one row for each of the four methods. '
                     'Every query lacking any definitive row is selected; every exclusion has a definitive row. '
                     'Original errors, validation failures, timeouts and memory-limit flags are retained verbatim. '
                     'Native definitive rows carry independent checks; external verdicts remain tool-reported.')
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'selection-audit.json', audit)
    result = dict(
        format='smpt-classic-v1', expected_properties=len(records), queries=records,
        selection='All and only jointly unresolved queries in the complete 60-second, four-method, one-repeat hard-development-v2 matrix.',
        scope='Outcome-selected development follow-up, not held-out evaluation or new independent inputs. '
              'Report six FastForward and two synthetic pigeonhole queries separately; retain 69/620 denominators. '
              'Unknown includes resource and validation failures and is never an unreachability proof.',
        source_evidence=dict(corpus=str(paths[0].relative_to(ROOT)), full_denominator=69,
                             parent_denominator=620, methods=METHODS, seconds=60, repeat=1,
                             sources=audit['sources'], selected=selected),
        selection_audit='selection-audit.json', selection_audit_sha256=digest(output / 'selection-audit.json'),
        generator_sha256=digest(Path(__file__)),
        portability='Inputs are unchanged sibling-corpus files. Preserve relative layout; source_mapping paths rebased from original corpus. source_lola/source_formula retain upstream archive paths; corresponding _local paths locate verified originals.')
    write_json(output / 'manifest.json', result)
    (output / 'builder.py').write_bytes(Path(__file__).read_bytes())
    (output / 'README.md').write_text(
        '# Hard survivors v1\n\n'
        'All eight jointly unresolved queries from the complete 276-row hard-development-v2 run: '
        'six FastForward random-walk queries and two synthetic pigeonhole queries. '
        'The full selection denominator remains 69, drawn from 620 parent queries. '
        'This is an outcome-selected development follow-up, not independent evaluation.\n\n'
        '`selection-audit.json` preserves every row, all 69 selection decisions, parent evidence hashes, '
        'and verified input identities. No unknown query was excluded; failures remain failures. '
        'Five selected rows carry memory-limit flags and 31 carry outer-timeout flags; flags overlap. '
        'Reserved evaluation families remain excluded.\n\n'
        'The manifest references unchanged sibling corpora. Transfer those corpora with this directory. '
        'Run `python3 scripts/build_hard_survivors.py --output benchmarks/another-name` to reproduce '
        'selection; normalized input paths depend on the output directory. '
        'The registered 300-second run has not been launched.\n')
    print(json.dumps(dict(properties=len(records), selected=selected,
                          manifest_sha256=digest(output / 'manifest.json'),
                          input_validation=audit['input_validation'])))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'benchmarks/hard-survivors-v1')
    build(parser.parse_args().output.resolve())
