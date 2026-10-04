#!/usr/bin/env python3
"""Strictly parse pinned repository LoLA pairs and inventory conversion requirements.

This does not run a solver or equate repository inputs with the archived artifact.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

U64_MAX = 2**64 - 1
I64_MAX = 2**63 - 1


def parse_net(text):
    header = re.match(r'\s*PLACE\s+([^;]*);\s*MARKING\s+([^;]*);', text)
    if not header:
        raise ValueError('unsupported PLACE/MARKING header')
    places = [p.strip() for p in header[1].split(',')]
    if not places or any(not p or re.search(r'\s', p) for p in places) or len(set(places)) != len(places):
        raise ValueError('empty, duplicate, or unsupported place identifiers')
    ids = {p: i for i, p in enumerate(places)}

    def arcs(source):
        result = []
        seen = set()
        for item in source.split(','):
            if not item.strip():
                if source.strip():
                    raise ValueError('empty list item')
                continue
            match = re.fullmatch(r'\s*(\S+)\s*:\s*(\d+)\s*', item)
            if not match or match[1] not in ids:
                raise ValueError(f'unknown or malformed arc: {item[:100]}')
            place, weight = ids[match[1]], int(match[2])
            if place in seen or weight > U64_MAX:
                raise ValueError('duplicate or oversized arc')
            seen.add(place)
            if weight:
                result.append([place, weight])
        return sorted(result)

    initial = [0] * len(places)
    for place, count in arcs(header[2]):
        initial[place] = count
    offset = header.end()
    transitions = []
    names = set()
    pattern = re.compile(r'\s*TRANSITION\s+([^\n]+)\s+CONSUME\s*([^;]*);\s*PRODUCE\s*([^;]*);')
    while offset < len(text):
        match = pattern.match(text, offset)
        if not match and not text[offset:].strip():
            break
        if not match:
            raise ValueError(f'unsupported transition syntax at byte {offset}')
        name = match[1].strip()
        if name in names:
            raise ValueError('duplicate transition identifier')
        names.add(name)
        transitions.append({'name': name, 'pre': arcs(match[2]), 'post': arcs(match[3])})
        offset = match.end()
    return {'places': places, 'initial': initial, 'transitions': transitions}


def parse_formula(text, places, max_branches=1024):
    tokens = []
    token_pattern = re.compile(r'\s*(>=|=|\(|\)|[^\s()=<>]+)')
    offset = 0
    while offset < len(text):
        match = token_pattern.match(text, offset)
        if not match:
            if not text[offset:].strip():
                break
            raise ValueError('unsupported formula token')
        tokens.append(match[1])
        offset = match.end()
    if not tokens or tokens[0] != 'EF':
        raise ValueError('only EF formulas supported')
    ids = {p: i for i, p in enumerate(places)}
    cursor = 1

    def take(token):
        nonlocal cursor
        if cursor >= len(tokens) or tokens[cursor] != token:
            raise ValueError(f'expected {token}')
        cursor += 1

    def factor(depth):
        nonlocal cursor
        if depth > 256:
            raise ValueError('formula depth limit')
        if cursor >= len(tokens):
            raise ValueError('truncated formula')
        if tokens[cursor] == '(':
            take('(')
            result = expression(depth + 1)
            take(')')
            return result
        place = tokens[cursor]
        cursor += 1
        if place not in ids or cursor + 1 >= len(tokens):
            raise ValueError('unknown place or truncated predicate')
        operator, constant = tokens[cursor:cursor + 2]
        cursor += 2
        if operator not in ('=', '>=') or not constant.isdecimal() or int(constant) > I64_MAX:
            raise ValueError('unsupported predicate')
        return [[(ids[place], int(constant), operator == '=')]]

    def conjunction(depth):
        result = factor(depth)
        while cursor < len(tokens) and tokens[cursor] == 'AND':
            take('AND')
            right = factor(depth)
            if len(result) * len(right) > max_branches:
                raise ValueError('formula branch limit')
            if len(result) == len(right) == 1:
                result[0].extend(right[0])
            else:
                result = [a + b for a in result for b in right]
        return result

    def expression(depth):
        result = conjunction(depth)
        while cursor < len(tokens) and tokens[cursor] == 'OR':
            take('OR')
            result += conjunction(depth)
            if len(result) > max_branches:
                raise ValueError('formula branch limit')
        return result

    result = expression(0)
    if cursor != len(tokens):
        raise ValueError('unconsumed formula syntax')
    return result


def canonical_branches(net, predicates):
    result = []
    for branch in predicates:
        target = []
        for place, bound, equality in branch:
            if bound == 0 and not equality:
                continue
            coefficients = [0] * len(net['places'])
            coefficients[place] = 1
            target.append({'coefficients': coefficients, 'bound': bound, 'equality': equality})
        result.append(dict(net, target=target))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('benchmarks/fastforward-repository-v1'))
    parser.add_argument('--output', type=Path, default=Path('research/fastforward-format-audit.json'))
    args = parser.parse_args()
    manifest = json.loads((args.source / 'acquisition.json').read_text())
    files = {f['path']: f for f in manifest['files']}
    rows = []
    for path, entry in files.items():
        if not path.endswith('.lola'):
            continue
        formula = path[:-5] + '.formula'
        row = {'path': path, 'formula': formula, 'suite': path.split('/')[3]}
        try:
            contents = []
            for name in (path, formula):
                data = (args.source / 'upstream' / name).read_bytes()
                if hashlib.sha256(data).hexdigest() != files[name]['sha256']:
                    raise ValueError('source SHA256 mismatch')
                contents.append(data.decode())
            net = parse_net(contents[0])
            predicates = parse_formula(contents[1], net['places'])
            constraints = sum(sum(equality or bound != 0 for _, bound, equality in branch) for branch in predicates)
            row.update(status='parsed-not-converted', places=len(net['places']), transitions=len(net['transitions']),
                       branches=len(predicates), predicates=sum(map(len, predicates)), nontrivial_constraints=constraints,
                       equality_zero_predicates=sum(bound == 0 and equality for branch in predicates for _, bound, equality in branch),
                       dense_coefficient_entries=constraints * len(net['places']))
        except (ValueError, KeyError, UnicodeError) as error:
            row.update(status='unsupported', error=str(error))
        rows.append(row)
    audit = {'format': 'fastforward-format-audit-v1', 'commit': manifest['commit'],
             'scope': 'Syntactic conversion audit only; no solver results or archive correspondence claims.',
             'counts': dict(Counter(r['status'] for r in rows)), 'queries': rows}
    if args.output.exists():
        raise ValueError('refusing to overwrite audit')
    args.output.write_text(json.dumps(audit, indent=2) + '\n')
    print(json.dumps(audit['counts']))
    for suite in ('coverability', 'random_walk', 'sypet'):
        good = [r for r in rows if r['suite'] == suite and r['status'] == 'parsed-not-converted']
        if good:
            print(suite, 'count', len(good), 'places', min(r['places'] for r in good), max(r['places'] for r in good),
                  'transitions', min(r['transitions'] for r in good), max(r['transitions'] for r in good),
                  'dense_entries', sum(r['dense_coefficient_entries'] for r in good))

if __name__ == '__main__':
    main()
