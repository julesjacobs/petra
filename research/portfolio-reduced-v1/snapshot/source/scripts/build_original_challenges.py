#!/usr/bin/env python3
"""Freeze measured development challenges from a complete audited comparison."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from analyze_original_comparison import analyze, DEFINITIVE


def select_views(report, candidate, competitors):
    methods = set(report['stable_solved'])
    if candidate not in methods or not competitors or not set(competitors) <= methods or candidate in competitors:
        raise ValueError('Select one measured candidate and distinct measured competitors')
    views = {key: [] for key in ('candidate-not-stable', 'competitor-only', 'joint-unresolved')}
    for case in report['cases']:
        answers = case['verdicts']
        stable = lambda method: all(v in DEFINITIVE for v in answers[method])
        if not stable(candidate):
            views['candidate-not-stable'].append(case['query'])
            if any(stable(m) for m in competitors):
                views['competitor-only'].append(case['query'])
        if all(v not in DEFINITIVE for m in (candidate, *competitors) for v in answers[m]):
            views['joint-unresolved'].append(case['query'])
    return views


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--results', type=Path, required=True)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--competitor', action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--group-by', choices=['family', 'suite'], default='family')
    args = parser.parse_args()
    paths = [args.corpus/'manifest.json', args.results/'environment.json', args.results/'runs.jsonl']
    manifest, environment = (json.loads(p.read_text()) for p in paths[:2])
    if hashlib.sha256(paths[0].read_bytes()).hexdigest() != environment['manifest_sha256']:
        raise ValueError('Corpus does not match measured manifest')
    report = analyze(manifest, environment,
                     [json.loads(line) for line in paths[2].read_text().splitlines()], args.group_by)
    views = select_views(report, args.candidate, args.competitor)
    report.update(format='measured-development-challenges-v1', corpus=str(args.corpus),
                  candidate=args.candidate, competitors=args.competitor, views=views,
                  measurement={key: environment.get(key) for key in
                               ('seconds', 'repeat', 'linux_cpus', 'perf', 'memory_mib', 'platform')},
                  sources={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                  scope='Outcome-selected development views; never use as held-out evidence. '
                        'Unknown/error is not unreachability. Retain the full corpus denominator. '
                        'Native answers independently checked; competitor answers tool-reported.')
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output/'views.json').write_text(json.dumps(report, indent=2)+'\n')
    for view, names in views.items():
        (args.output/(view+'.filter')).write_text(
            ('^(?:'+'|'.join(map(re.escape, names))+')$' if names else '(?!)')+'\n')
    lines = ['# Measured development challenges', '', report['scope'], '',
             f"Full denominator: {report['properties']} properties; {report['repeats']} repetition(s).",
             f"Apply filters to `{args.corpus}`. Candidate: `{args.candidate}`.", '',
             '| View | Properties | Meaning |', '|---|---:|---|']
    meanings = ['Candidate failed to solve in at least one repetition.',
                'A competitor solved in every repetition; candidate did not.',
                'Candidate and selected competitors returned no definitive answer in any repetition.']
    lines.extend(f'| {name} | {len(names)} | {meaning} |'
                 for (name, names), meaning in zip(views.items(), meanings))
    lines += ['', 'These filters overlap. Keep original PNML/XML and charge parsing and preprocessing.',
              'Do not pool these selected cases into a new headline score.', '']
    (args.output/'README.md').write_text('\n'.join(lines))
    print(json.dumps({key: len(value) for key, value in views.items()}))


if __name__ == '__main__':
    main()
