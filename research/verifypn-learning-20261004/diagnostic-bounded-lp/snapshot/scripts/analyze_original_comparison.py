#!/usr/bin/env python3
"""Audit complete original-input comparisons before reporting coverage."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics

DEFINITIVE = {'reachable', 'unreachable'}


def analyze(manifest, environment, rows, group_by="family"):
    if group_by not in ('family', 'suite'):
        raise ValueError('Expected family or suite grouping')
    names = environment['property_order']
    methods, repeats = environment['methods'], environment['repeat']
    queries = {q['name']: q for q in manifest['queries']}
    if len(set(names)) != len(names) or not set(names) <= set(queries):
        raise ValueError('Invalid selected properties')
    matrix = {(r['query'], r['method'], r['repeat']): r for r in rows}
    if len(matrix) != len(rows) or set(matrix) != {
            (n, m, i) for n in names for m in methods for i in range(repeats)}:
        raise ValueError('Incomplete, duplicated or unexpected matrix')
    native = set(environment.get('native_tools', {}))
    for name in names:
        answers = {matrix[name, m, i]['verdict'] for m in methods for i in range(repeats)} & DEFINITIVE
        if len(answers) > 1:
            raise ValueError(f'Definitive disagreement: {name}')
    for row in rows:
        if row['method'] not in native or row['verdict'] not in DEFINITIVE:
            continue
        branches = row.get('branches', [])
        checked = lambda b, verdict: b.get('verdict') == verdict and b.get('independent_check', '').startswith('python-')
        if row['verdict'] == 'reachable':
            valid = any(checked(b, 'reachable') for b in branches)
        else:
            expected = len(queries[row['query']]['branches'])
            valid = len(branches) == expected and {b['branch'] for b in branches} == set(range(expected)) and all(
                checked(b, 'unreachable') for b in branches)
        if not valid:
            raise ValueError(f'Unchecked native answer: {row["query"]}/{row["method"]}')
    solved = {m: {n for n in names if all(matrix[n, m, i]['verdict'] in DEFINITIVE
                                        for i in range(repeats))} for m in methods}
    result = dict(properties=len(names), rows=len(rows), repeats=repeats,
                  counts={m: dict(Counter(r['verdict'] for r in rows if r['method'] == m)) for m in methods},
                  stable_solved={m: len(s) for m, s in solved.items()},
                  comparisons={}, cases=[])
    group_key = 'families' if group_by == 'family' else 'suites'
    result[group_key] = {}
    for group in sorted({queries[n][group_by] for n in names}):
        members = {n for n in names if queries[n][group_by] == group}
        result[group_key][group] = dict(properties=len(members),
                                       solved={m: len(s & members) for m, s in solved.items()})
    for previous in methods:
        for candidate in methods:
            if previous == candidate:
                continue
            common = sorted(solved[previous] & solved[candidate])
            ratios = [statistics.median(matrix[n, candidate, i]['wall_seconds'] for i in range(repeats)) /
                      statistics.median(matrix[n, previous, i]['wall_seconds'] for i in range(repeats))
                      for n in common]
            result['comparisons'][previous+' -> '+candidate] = dict(
                gained=sorted(solved[candidate]-solved[previous]), lost=sorted(solved[previous]-solved[candidate]),
                common_solved=len(common), median_candidate_previous_wall_ratio=statistics.median(ratios) if ratios else None,
                timing_scope='Conditional on both methods solving in every repetition; excludes unresolved properties.')
    for name in sorted(names):
        result['cases'].append(dict(query=name, **{group_by: queries[name][group_by]},
            verdicts={m: [matrix[name,m,i]['verdict'] for i in range(repeats)] for m in methods}))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--results', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--group-by', choices=['family', 'suite'], default='family')
    args = parser.parse_args()
    paths = [args.corpus/'manifest.json', args.results/'environment.json', args.results/'runs.jsonl']
    manifest, environment = (json.loads(p.read_text()) for p in paths[:2])
    rows = [json.loads(line) for line in paths[2].read_text().splitlines()]
    if hashlib.sha256(paths[0].read_bytes()).hexdigest() != environment['manifest_sha256']:
        raise ValueError('Corpus does not match measured manifest')
    report = analyze(manifest, environment, rows, args.group_by)
    report['sources'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    report['scope'] = 'Development comparison; original-input native answers independently checked, external answers tool-reported. Full selected denominator retained.'
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    group_key = 'families' if args.group_by == 'family' else 'suites'
    print(json.dumps({k: report[k] for k in ('properties','rows','stable_solved',group_key)}, indent=2))


if __name__ == '__main__':
    main()
