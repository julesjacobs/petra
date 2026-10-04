#!/usr/bin/env python3
"""Timed Python PNML/XML frontend for the Rust reachability backend.

Run under an outer process-tree deadline. This frontend records proposals;
the benchmark parent independently checks every definitive backend answer.
"""
import argparse
import json
import math
import pathlib
import subprocess
import time

from smpt_import import dnf, only, pnml, require, xml_tree


def translate(net, xml, property_id):
    problem = pnml(net)
    root = xml_tree(xml)
    require(root.tag == 'property-set', 'Expected property-set')
    selected = [p for p in root if p.tag == 'property' and p.findtext('id') == property_id]
    require(len(selected) == 1, 'Requested property ID must occur exactly once')
    formula = only(selected[0].find('formula'))
    temporal = only(formula)
    kind = (formula.tag, temporal.tag)
    require(kind in [('exists-path', 'finally'), ('all-paths', 'globally')], 'Only EF and AG supported')
    invariant = kind[0] == 'all-paths'
    targets = dnf(only(temporal), {name: i for i, name in enumerate(problem['places'])}, invariant)
    return problem, dict(property_id=property_id, kind='AG' if invariant else 'EF', targets=targets)


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value) + '\n')
    temporary.replace(path)


def solve(args):
    deadline = time.monotonic() + args.seconds
    args.artifacts.mkdir(parents=True, exist_ok=False)
    problem, prop = translate(args.pnml, args.xml, args.property_id)
    for i, target in enumerate(prop['targets']):
        write_json(args.artifacts / f'branch-{i}.json', dict(problem, target=target))
    write_json(args.artifacts / 'translation.json', dict(
        property_id=prop['property_id'], kind=prop['kind'], branch_count=len(prop['targets'])))
    records = []
    for i in range(len(prop['targets'])):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        budget = remaining / (len(prop['targets']) - i)
        command = [str(args.binary), '--json', str(args.artifacts / f'branch-{i}.json'),
                   '--method', args.method, '--seconds', str(budget),
                   '--max-states', str(args.max_states)]
        start = time.monotonic()
        with (args.artifacts / f'answer-{i}.json').open('w') as output:
            try:
                process = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT, timeout=budget)
                code, expired = process.returncode, False
            except subprocess.TimeoutExpired:
                code, expired = None, True
        record = dict(branch=i, wall_seconds=time.monotonic()-start,
                      exit_code=code, outer_timeout=expired, command=command)
        records.append(record)
        write_json(args.artifacts / 'attempts.json', records)
        if not expired and code == 0:
            try:
                answer = json.loads((args.artifacts / f'answer-{i}.json').read_text())
                if answer.get('verdict') == 'reachable':
                    break
            except (ValueError, AttributeError):
                pass
    return dict(property_id=prop['property_id'], kind=prop['kind'],
                branch_count=len(prop['targets']), attempts=records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('pnml', 'xml', 'binary', 'artifacts'):
        parser.add_argument('--'+name, type=pathlib.Path, required=True)
    parser.add_argument('--property-id', required=True)
    parser.add_argument('--method', required=True)
    parser.add_argument('--seconds', type=float, required=True)
    parser.add_argument('--max-states', type=int, default=200000)
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or args.seconds <= 0:
        parser.error('Positive finite seconds required')
    try:
        print(json.dumps(solve(args)))
    except Exception as error:
        print(json.dumps(dict(error=repr(error))))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
