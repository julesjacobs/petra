#!/usr/bin/env python3
"""Package outcome-selected development views without changing the full corpus."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
METHODS = ('candidate-python', 'candidate-rust', 'verifypn-default')
DEFINITIVE = {'reachable', 'unreachable'}


def analyze(manifest, rows):
    queries = {q['name']: q for q in manifest['queries']}
    if len(queries) != len(manifest['queries']):
        raise ValueError('Duplicate manifest query')
    matrix = {}
    for row in rows:
        key = row['query'], row['method']
        if row['repeat'] != 0 or key in matrix:
            raise ValueError('Expected one complete repetition')
        matrix[key] = row
    if set(matrix) != {(q, m) for q in queries for m in METHODS}:
        raise ValueError('Incomplete or unexpected benchmark matrix')
    views = {name: [] for name in (
        'candidate-unresolved', 'both-candidates-unresolved', 'all-unresolved',
        'verifypn-only', 'candidate-only', 'any-unresolved')}
    families = {}
    cases = []
    for name, query in sorted(queries.items()):
        results = {m: matrix[name, m] for m in METHODS}
        answers = {r['verdict'] for r in results.values()} & DEFINITIVE
        if len(answers) > 1:
            raise ValueError(f'Definitive disagreement: {name}')
        solved = {m: r['verdict'] in DEFINITIVE for m, r in results.items()}
        py, rust, verify = (solved[m] for m in METHODS)
        conditions = (not rust, not py and not rust, not any(solved.values()),
                      verify and not rust, rust and not verify, not all(solved.values()))
        for view, selected in zip(views, conditions):
            if selected:
                views[view].append(name)
        counts = families.setdefault(query['family'], Counter())
        counts['properties'] += 1
        for method in METHODS:
            counts[method] += solved[method]
        counts['all-unresolved'] += not any(solved.values())
        cases.append(dict(query=name, family=query['family'],
                          pnml_sha256=query['pnml_sha256'], xml_sha256=query['xml_sha256'],
                          verdicts={m: r['verdict'] for m, r in results.items()}))
    return dict(full_denominator=len(queries), families=families, views=views, cases=cases)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=Path, default=ROOT/'benchmarks/mcc-stress-development')
    parser.add_argument('--results', type=Path, default=ROOT/'results/linux-stress-paired-frontends-v1')
    parser.add_argument('--output', type=Path, default=ROOT/'benchmarks/stress-challenges-v1')
    args = parser.parse_args()
    manifest = args.corpus/'manifest.json'
    runs = args.results/'runs.jsonl'
    result = analyze(json.loads(manifest.read_text()),
                     [json.loads(line) for line in runs.read_text().splitlines()])
    result.update(format='stress-challenge-views-v1',
                  scope='Outcome-selected development views. Unknown is not unreachability. '
                        'Report the full corpus separately; these are not held-out evaluation.',
                  sources={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in (manifest, runs)})
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output/'views.json').write_text(json.dumps(result, indent=2)+'\n')
    for name, names in result['views'].items():
        expression = '^(?:'+'|'.join(map(re.escape, names))+')$' if names else '(?!)'
        (args.output/(name+'.filter')).write_text(expression+'\n')
    lines = ['# Stress development challenge sets', '', result['scope'], '',
             'Selection uses the completed 5-second, single-core Linux comparison, with a 2 GiB limit.',
             'All filters operate on `benchmarks/mcc-stress-development`; inputs are not copied or modified.',
             '', '| View | Properties |', '|---|---:|']
    lines.extend(f'| {name} | {len(names)} |' for name, names in result['views'].items())
    lines += ['', 'Candidate means the Rust frontend in candidate-only/verifypn-only views.',
              'Both candidate configurations use the same frozen engine with different frontends.',
              '', 'Pass a filter file as the existing benchmark runner’s `--filter` argument.',
              'Use the full 368-property corpus for headline comparisons.', '',
              '| Family | Total | Python frontend | Rust frontend | VerifyPN | All unresolved |',
              '|---|---:|---:|---:|---:|---:|']
    for family, c in sorted(result['families'].items()):
        lines.append('| '+family+' | '+' | '.join(str(c[k]) for k in ('properties', *METHODS, 'all-unresolved'))+' |')
    (args.output/'README.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({name: len(names) for name, names in result['views'].items()}))


if __name__ == '__main__':
    main()
