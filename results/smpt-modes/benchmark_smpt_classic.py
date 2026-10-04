#!/usr/bin/env python3
"""Sequential, whole-property benchmarks for the published SMPT suites."""
import argparse
import collections
import hashlib
import json
import math
import os
import pathlib
import platform
import re
import sys

from benchmark import run, verify

ROOT = pathlib.Path(__file__).resolve().parents[1]
SMPT_MODES = {
    'smpt': ['STATE-EQUATION', 'BMC'],
    'smpt-state-equation': ['STATE-EQUATION'],
    'smpt-bmc': ['BMC'],
    'smpt-induction': ['INDUCTION'],
    'smpt-k-induction': ['K-INDUCTION'],
    'smpt-pdr-cov': ['PDR-COV'],
    'smpt-pdr-reach': ['PDR-REACH'],
    'smpt-pdr-saturated': ['PDR-REACH-SATURATED'],
    'smpt-portfolio': ['STATE-EQUATION', 'BMC', 'INDUCTION', 'K-INDUCTION',
                       'PDR-COV', 'PDR-REACH', 'PDR-REACH-SATURATED'],
}


def aggregate(verdicts):
    if 'error' in verdicts:
        return 'error'
    if 'reachable' in verdicts:
        return 'reachable'
    if all(v == 'unreachable' for v in verdicts):
        return 'unreachable'
    return 'unknown'


def property_truth(kind, verdict):
    if verdict not in ('reachable', 'unreachable'):
        return None
    return (verdict == 'reachable') == (kind == 'EF')


def checked(path, digest):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(f'Input checksum mismatch: {path}')
    return data


def native(query, corpus, output, method, repeat, args):
    verdicts, checks, branches = [], [], []
    wall = 0.0
    for i, branch in enumerate(query['branches']):
        if 'reachable' in verdicts or wall >= args.seconds:
            if 'reachable' not in verdicts:
                verdicts.append('unknown')
            break
        path = corpus/branch['path']
        problem = json.loads(checked(path, branch['sha256']))
        budget = (args.seconds-wall)/(len(query['branches'])-i)
        log = output/f'{query["name"]}.{method}.{repeat}.branch-{i}.json'
        command = [str(args.binary), '--json', str(path), '--method', method,
                   '--seconds', str(budget), '--max-states', str(args.max_states)]
        elapsed, code, expired = run(command, ROOT, budget+0.5, log)
        wall += elapsed
        result = dict(branch=i, wall_seconds=elapsed, exit_code=code, outer_timeout=expired)
        verdict = 'unknown'
        if not expired:
            try:
                if code != 0:
                    raise ValueError(f'Solver exit code {code}')
                answer = json.loads(log.read_text())
                verdict = answer['verdict']
                if verdict not in ('reachable', 'unreachable', 'unknown'):
                    raise ValueError(f'Invalid verdict {verdict}')
                check = verify(problem, answer)
                checks.append(check)
                result.update(independent_check=check, engine=answer['method'])
            except Exception as error:
                verdict = 'error'
                result['error'] = repr(error)
        verdicts.append(verdict)
        branches.append(dict(result, verdict=verdict))
    return dict(verdict=aggregate(verdicts), wall_seconds=wall, branches=branches,
                independent_checks=checks)


def smpt(query, corpus, output, method, repeat, args):
    log = output/f'{query["name"]}.{method}.{repeat}.log'
    command = [str(ROOT/'vendor/venv/bin/python'), '-m', 'smpt',
               '-n', str(corpus/query['net']), '--xml', str(corpus/query['property']),
               '--methods', *SMPT_MODES[method], '--timeout', str(math.ceil(args.seconds)),
               '--show-time', '--show-techniques', '--show-model', '--export-proof', str(log.with_suffix('.proof'))]
    wall, code, expired = run(command, ROOT/'vendor/SMPT', args.seconds+1, log)
    contents = log.read_text()
    match = re.search(r'^FORMULA \S+ (TRUE|FALSE)(?: |$)', contents, re.M)
    verdict = 'unknown'
    if match:
        truth = match[1] == 'TRUE'
        verdict = 'reachable' if truth == (query['kind'] == 'EF') else 'unreachable'
    elif (code and not expired) or 'Traceback (most recent call last):' in contents:
        verdict = 'error'
    return dict(verdict=verdict, wall_seconds=wall, exit_code=code,
                outer_timeout=expired, enabled_methods=SMPT_MODES[method],
                subprocess_error='Traceback (most recent call last):' in contents,
                formula_output=next((line for line in contents.splitlines() if line.startswith('FORMULA ')), None),
                independent_checks=['none-external-smpt'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=pathlib.Path, default=ROOT/'benchmarks/smpt-classic')
    parser.add_argument('--output', type=pathlib.Path, default=ROOT/'results/smpt-classic')
    parser.add_argument('--binary', type=pathlib.Path, default=ROOT/'target/release/vass-reach')
    parser.add_argument('--methods', nargs='+', default=['portfolio-next', 'smpt'])
    parser.add_argument('--seconds', type=float, default=2)
    parser.add_argument('--repeat', type=int, default=1)
    parser.add_argument('--max-states', type=int, default=200000)
    parser.add_argument('--filter', default='')
    args = parser.parse_args()
    if any(m.startswith('smpt') and m not in SMPT_MODES for m in args.methods):
        parser.error('Unknown SMPT configuration; available: '+', '.join(SMPT_MODES))
    if not math.isfinite(args.seconds) or args.seconds <= 0 or args.repeat < 1:
        parser.error('Positive finite seconds and positive repeat required')
    args.binary = args.binary.resolve()
    corpus, output = args.corpus.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest = corpus/'manifest.json'
    queries = [q for q in json.loads(manifest.read_text())['queries'] if re.search(args.filter, q['name'])]
    for q in queries:
        if q['status'] == 'imported':
            checked(corpus/q['net'], q['net_sha256'])
            checked(corpus/q['property'], q['property_sha256'])
            for branch in q['branches']:
                checked(corpus/branch['path'], branch['sha256'])
    environment = dict(seconds=args.seconds, repeat=args.repeat, methods=args.methods,
                       max_states=args.max_states, platform=platform.platform(),
                       queries=len(queries), manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
                       binary_sha256=hashlib.sha256(args.binary.read_bytes()).hexdigest(),
                       script_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                      for p in [pathlib.Path(__file__), ROOT/'scripts/smpt_import.py', ROOT/'scripts/benchmark.py']},
                       scope='Whole original properties; sequential cold processes. Native branches share a budget; AG answers invert counterexample reachability. Verification excluded from wall time.',
                       smpt_configurations={m: SMPT_MODES[m] for m in args.methods if m in SMPT_MODES},
                       smpt_source_sha256={str(p.relative_to(ROOT/'vendor/SMPT')): hashlib.sha256(p.read_bytes()).hexdigest()
                                           for p in sorted((ROOT/'vendor/SMPT/smpt').rglob('*.py'))},
                       smpt='Existing SER artifact SMPT, no net reductions; ceil(seconds) internal timeout and seconds+1 outer timeout. K-INDUCTION automatically adds BMC. PDR-COV applies only to monotone targets. Portfolio methods execute concurrently inside SMPT. No independent SMPT proof check.')
    (output/'environment.json').write_text(json.dumps(environment, indent=2)+'\n')
    os.environ['PATH'] = str(ROOT/'vendor/venv/bin')+os.pathsep+os.environ['PATH']
    rows = []
    with (output/'runs.jsonl').open('w') as records:
        for query in queries:
            for repeat in range(args.repeat):
                for method in args.methods if repeat % 2 == 0 else args.methods[::-1]:
                    if query['status'] != 'imported':
                        result = dict(verdict='unsupported', error=query.get('error'))
                    else:
                        result = smpt(query, corpus, output, method, repeat, args) if method in SMPT_MODES else native(query, corpus, output, method, repeat, args)
                    row = dict(query=query['name'], suite=query['suite'], method=method, repeat=repeat,
                               property_kind=query.get('kind'), **result)
                    row['property_truth'] = property_truth(query.get('kind'), row['verdict'])
                    rows.append(row)
                    records.write(json.dumps(row)+'\n')
                    records.flush()
                    print(query['name'], method, row['verdict'], row['property_truth'], flush=True)
    lines = ['# Published SMPT suites', '', f'{len(queries)} original properties; {args.seconds}s budget; {args.repeat} repetition(s).', '',
             '| Method | Reachable | Unreachable | Unknown | Errors/unsupported/unstable |', '|---|---:|---:|---:|---:|']
    for method in args.methods:
        groups = collections.defaultdict(set)
        for row in rows:
            if row['method'] == method:
                groups[row['query']].add(row['verdict'])
        counts = collections.Counter(next(iter(v)) if len(v) == 1 else 'unstable' for v in groups.values())
        lines.append(f'| {method} | {counts["reachable"]} | {counts["unreachable"]} | {counts["unknown"]} | {sum(counts[k] for k in ("error", "unsupported", "unstable"))} |')
    disagreements = []
    for query in queries:
        answers = {r['property_truth'] for r in rows if r['query'] == query['name'] and r['property_truth'] is not None}
        if len(answers) > 1:
            disagreements.append(query['name'])
    lines += ['', 'Reachability refers to EF targets or AG counterexamples; `property_truth` in runs.jsonl preserves the original property polarity.',
              'Certificate examples duplicate two expressiveness examples and are retained as a separate published suite. No external verdict is treated as an oracle.',
              f'Definitive disagreements: {disagreements}.',
              'Native witnesses and available certificates are checked independently; per-branch verification status is recorded. SMPT proofs are not independently checked. Timings are exploratory on a shared host.']
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n')
    if disagreements or any(r['verdict'] == 'error' for r in rows):
        sys.exit(1)


if __name__ == '__main__':
    main()
