#!/usr/bin/env python3
"""Audit the complete five-method DAG development comparison and make filters."""
import hashlib
import json
from collections import Counter
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
METHODS = ('before', 'dag-v1', 'symbolic', 'verifypn-default', 'smpt-full-portable')
DEFINITIVE = {'reachable', 'unreachable'}


def analyze(manifest, rows):
    names = [q['name'] for q in manifest['queries']]
    if len(set(names)) != len(names):
        raise ValueError('Duplicate query')
    matrix = {}
    for row in rows:
        key = row['query'], row['method']
        if row['repeat'] != 0 or key in matrix:
            raise ValueError('Expected exactly one repetition')
        matrix[key] = row
    if set(matrix) != {(name, method) for name in names for method in METHODS}:
        raise ValueError('Incomplete or unexpected matrix')
    for name in names:
        answers = {matrix[name, method]['verdict'] for method in METHODS} & DEFINITIVE
        if len(answers) > 1:
            raise ValueError(f'Definitive disagreement: {name}')
        for method in METHODS[:3]:
            row = matrix[name, method]
            checks = row.get('independent_checks', [])
            if row['verdict'] in DEFINITIVE and (
                    not checks or any(not c.startswith('python-') for c in checks)):
                raise ValueError(f'Unchecked native result: {name}/{method}')
    solved = {method: {name for name in names
                      if matrix[name, method]['verdict'] in DEFINITIVE}
              for method in METHODS}
    all_names = set(names)
    views = {
        'candidate-unresolved': all_names - solved['symbolic'],
        'all-unresolved': all_names - set.union(*solved.values()),
        'competitor-only': (solved['verifypn-default'] | solved['smpt-full-portable'])
                           - solved['symbolic'],
        'candidate-only': solved['symbolic']
                          - solved['verifypn-default'] - solved['smpt-full-portable'],
    }
    return dict(
        full_denominator=len(names), rows=len(rows),
        scope='Outcome-selected synthetic development views; one 5-second single-core '
              'Linux repetition, 2 GiB. Native certificates independently checked. '
              'Competitor answers are tool-reported. Unknowns and errors are not negative answers. '
              'Use all 34 queries for comparisons; these are not held-out evaluation.',
        counts={method: dict(Counter(matrix[name, method]['verdict'] for name in names))
                for method in METHODS},
        gained_over_predecessor=sorted(solved['symbolic'] - solved['before']),
        lost_from_predecessor=sorted(solved['before'] - solved['symbolic']),
        gained_over_dag_v1=sorted(solved['symbolic'] - solved['dag-v1']),
        lost_from_dag_v1=sorted(solved['dag-v1'] - solved['symbolic']),
        views={key: sorted(value) for key, value in views.items()},
        cases=[dict(query=name, verdicts={method: matrix[name, method]['verdict']
                                         for method in METHODS}) for name in sorted(names)],
    )


def main():
    manifest = ROOT / 'benchmarks/boolean-consistency-v3/manifest.json'
    runs = ROOT / 'results/linux-dag-sat-v2/runs.jsonl'
    report = analyze(json.loads(manifest.read_text()),
                     [json.loads(line) for line in runs.read_text().splitlines()])
    report['sources'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in (manifest, runs)}
    out = ROOT / 'benchmarks/boolean-consistency-challenges-v2'
    out.mkdir(exist_ok=False)
    encoded = json.dumps(report, indent=2) + '\n'
    (out / 'views.json').write_text(encoded)
    (ROOT / 'research/linux-dag-sat-v2-analysis.json').write_text(encoded)
    for view, names in report['views'].items():
        regex = '^(?:' + '|'.join(map(re.escape, names)) + ')$' if names else '(?!)'
        (out / (view + '.filter')).write_text(regex + '\n')
    lines = ['# Boolean-consistency comparison, v2', '', report['scope'], '',
             '| Method | Reachable | Unreachable | Unknown | Error |',
             '|---|---:|---:|---:|---:|']
    for method, counts in report['counts'].items():
        lines.append('| ' + method + ' | ' + ' | '.join(
            str(counts.get(k, 0)) for k in ('reachable', 'unreachable', 'unknown', 'error')) + ' |')
    lines += ['', '## Development filters', '',
              'Apply these filters to `benchmarks/boolean-consistency-v3`.', '']
    lines.extend(f'- `{view}.filter`: {len(names)} queries.'
                 for view, names in report['views'].items())
    lines += ['', 'The application comparison remains separate: the last complete 368-query',
              'run left 70 Rust queries unresolved, with 58 solved by VerifyPN.',
              'Synthetic gains do not establish an application performance advantage.', '']
    (out / 'README.md').write_text('\n'.join(lines))
    (ROOT / 'research/linux-dag-sat-v2-analysis.md').write_text('\n'.join(lines))
    print(json.dumps({k: v for k, v in report.items() if k != 'cases'}, indent=2))


if __name__ == '__main__':
    main()
