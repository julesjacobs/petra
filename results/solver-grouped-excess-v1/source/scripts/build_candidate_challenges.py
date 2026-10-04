#!/usr/bin/env python3
"""Freeze development cases unresolved by the recorded candidate configuration."""
import argparse
from collections import Counter, defaultdict
import copy
import json
import os
from pathlib import Path

from analyze_original_comparison import analyze, DEFINITIVE
from build_hard_development import ROOT, SOURCES, digest
from benchmark_smpt_classic import preflight_inputs


def build(output):
    reserved_path = ROOT / 'benchmarks/reserved-evaluation-v2.json'
    reserved = set(json.loads(reserved_path.read_text())['reserved_families'])
    queries, evidence = [], []
    for corpus_name, result_name in SOURCES:
        corpus = ROOT / 'benchmarks' / corpus_name
        results = ROOT / 'results' / result_name
        paths = [corpus / 'manifest.json', results / 'environment.json', results / 'runs.jsonl']
        manifest, env = [json.loads(p.read_text()) for p in paths[:2]]
        rows = [json.loads(line) for line in paths[2].read_text().splitlines()]
        if digest(paths[0]) != env['manifest_sha256']:
            raise ValueError(f'Changed corpus: {corpus_name}')
        if set(env['property_order']) != {q['name'] for q in manifest['queries']}:
            raise ValueError(f'Incomplete corpus comparison: {corpus_name}')
        group = 'family' if all('family' in q for q in manifest['queries']) else 'suite'
        report = analyze(manifest, env, rows, group_by=group)
        candidate = 'symbolic' if corpus_name == 'boolean-consistency-v3' else 'after'
        native = set(env['native_tools'])
        selected = {}
        for case in report['cases']:
            verdicts = case['verdicts']
            if all(v in DEFINITIVE for v in verdicts[candidate]):
                continue
            stable = [m for m, vs in verdicts.items() if all(v in DEFINITIVE for v in vs)]
            if any(m not in native for m in stable):
                category = 'competitor-solved'
            elif stable:
                category = 'other-native-solved'
            elif all(v == 'unknown' for vs in verdicts.values() for v in vs):
                category = 'joint-unknown'
            else:
                category = 'unresolved-with-errors-or-variation'
            selected[case['query']] = dict(category=category, **case)
        selected_rows = [r for r in rows if r['query'] in selected]
        evidence.append(dict(corpus=corpus_name, candidate=candidate,
            full_denominator=report['properties'], selected=len(selected),
            categories=dict(Counter(c['category'] for c in selected.values())),
            methods=env['methods'], native_tools=env['native_tools'],
            seconds=env['seconds'], repeat=env['repeat'],
            sources={str(p.relative_to(ROOT)): digest(p) for p in paths},
            failures=[dict(query=r['query'], method=r['method'], verdict=r['verdict'],
                           capability_failures=r.get('capability_failures', []))
                      for r in selected_rows if r['verdict'] not in DEFINITIVE | {'unknown'}
                      or r.get('capability_failures')],
            cases=list(selected.values())))
        for original in manifest['queries']:
            if original['name'] not in selected:
                continue
            if original.get('family_group', original.get('family')) in reserved:
                raise ValueError('Reserved family selected for development')
            q = copy.deepcopy(original)
            q['development_source'] = str(paths[0].relative_to(ROOT))
            q['challenge_category'] = selected[q['name']]['category']
            for key in ('pnml', 'xml', 'net', 'property', 'source_cnf', 'source_mapping'):
                if key in q:
                    q[key] = os.path.relpath(corpus / q[key], output)
            for branch in q['branches']:
                branch['path'] = os.path.relpath(corpus / branch['path'], output)
            queries.append(q)
    if len({q['name'] for q in queries}) != len(queries):
        raise ValueError('Query name collision')
    inputs = preflight_inputs(queries, output, original=True)
    groups = defaultdict(list)
    for q in queries:
        groups[tuple(sorted(b['sha256'] for b in q['branches']))].append(q['name'])
    manifest = dict(format='smpt-classic-v1', expected_properties=len(queries), queries=queries,
        selection='Every case not solved in every repetition by the recorded candidate; retain errors.',
        scope='Outcome-selected development view of existing data, not held-out evidence. '
              'Difficulty is specific to the recorded five-second configurations. '
              'Report source tracks and full parent denominators separately. '
              'Competitor answers are tool-reported; native definitive answers independently checked.',
        source_evidence=evidence, generator_sha256=digest(Path(__file__)),
        reserved_selection_sha256=digest(reserved_path),
        input_validation=dict(unique_files=len(inputs.seen), bytes_hashed=inputs.bytes_hashed),
        exact_branch_hash_duplicate_groups=[g for g in groups.values() if len(g) > 1],
        deduplication_scope='Canonical branch-file hashes only; no isomorphism or semantic-equivalence claim.',
        portability='References sibling source corpora; transfer those corpora with this view.')
    output.mkdir(parents=True, exist_ok=False)
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (output / 'builder.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps(dict(properties=len(queries), tracks=[
        {k: e[k] for k in ('corpus', 'selected', 'categories')} for e in evidence],
        duplicate_groups=manifest['exact_branch_hash_duplicate_groups'],
        manifest_sha256=digest(output / 'manifest.json')), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'benchmarks/candidate-challenges-v1')
    build(parser.parse_args().output.resolve())
