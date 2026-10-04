#!/usr/bin/env python3
"""Independent exact checking of token-cut-v1 negative certificates."""
import argparse
import collections
from fractions import Fraction
import json

from token_moment_checker import reconstruct_control


def master_rows(problem, controls, modes, edges, terminal):
    def equality(terms, bound):
        yield [(variable, -coefficient) for variable, coefficient in terms], -bound
        yield terms, bound

    effects = []
    for transition in problem['transitions']:
        effect = collections.defaultdict(int)
        for p, weight in transition['pre']:
            effect[p] -= weight
        for p, weight in transition['post']:
            effect[p] += weight
        effects.append(effect)
    for p, initial in enumerate(problem['initial']):
        terms = [(('final', p), 1)]
        terms.extend((('count', e), -effects[t][p]) for e, (_, _, t) in enumerate(edges))
        yield from equality(terms, initial)
    for p in controls:
        yield from equality([(('final', p), 1)], int(modes[terminal] == p))
    for constraint in problem['target']:
        terms = [(('final', p), a) for p, a in enumerate(constraint['coefficients'])]
        if constraint['equality']:
            yield from equality(terms, constraint['bound'])
        else:
            yield terms, constraint['bound']
    for q in range(len(modes)):
        terms = [(('count', e), int(source == q) - int(destination == q))
                 for e, (source, destination, _) in enumerate(edges)]
        yield from equality(terms, int(q == 0) - int(q == terminal))


def cut_row(problem, controls, modes, edges, terminal, cut, finite=None):
    """Derive outgoing capacity minus demand for the supplied mode subset."""
    assert set(cut) == {'place', 'modes'}
    place, subset = cut['place'], cut['modes']
    assert type(place) is int and 0 <= place < len(problem['places'])
    assert type(subset) is list and subset == sorted(set(subset))
    assert all(type(q) is int and 0 <= q < len(modes) for q in subset)
    assert type(terminal) is int and 0 <= terminal < len(modes)
    inside = set(subset)
    demands = [collections.defaultdict(int) for _ in modes]
    constants = [0 for _ in modes]
    constants[0] += problem['initial'][place]
    demands[terminal]['final', place] -= 1
    capacity = collections.defaultdict(int)
    for e, (source, destination, t) in enumerate(edges):
        transition = problem['transitions'][t]
        pre = dict(transition['pre']).get(place, 0)
        post = dict(transition['post']).get(place, 0)
        demands[source]['count', e] -= pre
        demands[destination]['count', e] += post
        if source in inside and destination not in inside:
            if place in controls:
                upper = int(modes[source] == place)
            else:
                assert finite is not None and finite[place] is not None, 'cut crosses an unbounded outgoing edge'
                upper = max(pre, finite[place])
            assert upper >= pre
            capacity['count', e] += upper - pre
    terms = capacity
    for q in subset:
        for variable, coefficient in demands[q].items():
            terms[variable] -= coefficient
    return list(terms.items()), sum(constants[q] for q in subset)


def verify_token_cut(problem, proof):
    assert set(proof) == {'kind', 'controls', 'terminals'}
    assert proof['kind'] == 'token-cut-v1'
    verify_terminals(problem, proof)
    return 'python-token-cut'


def verify_terminals(problem, proof, finite=None):
    """Check all terminal contradictions using independently certified bounds."""
    controls = proof['controls']
    modes, edges = reconstruct_control(problem, controls)
    assert type(proof['terminals']) is list and len(proof['terminals']) == len(modes)
    for terminal, leaf in enumerate(proof['terminals']):
        assert set(leaf) == {'cuts', 'multipliers'}
        assert type(leaf['cuts']) is list and type(leaf['multipliers']) is list
        rows = list(master_rows(problem, controls, modes, edges, terminal))
        rows.extend(cut_row(problem, controls, modes, edges, terminal, cut, finite) for cut in leaf['cuts'])
        lhs = collections.defaultdict(Fraction)
        rhs = Fraction(0)
        previous = -1
        for index, raw in leaf['multipliers']:
            assert type(index) is int and previous < index < len(rows)
            assert type(raw) is str
            weight = Fraction(raw)
            assert weight > 0
            previous = index
            terms, bound = rows[index]
            for variable, coefficient in terms:
                lhs[variable] += weight * coefficient
            rhs += weight * bound
        assert rhs > 0 and all(a <= 0 for a in lhs.values()), 'invalid Farkas contradiction'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('problem')
    parser.add_argument('certificate', help='proof object or solver answer containing a proof')
    args = parser.parse_args()
    with open(args.problem) as stream:
        problem = json.load(stream)
    with open(args.certificate) as stream:
        answer = json.load(stream)
    if 'proof' in answer:
        assert answer['verdict'] == 'unreachable'
        proof = answer['proof']
    else:
        proof = answer
    print(json.dumps(dict(checker=verify_token_cut(problem, proof), verified=True)))


if __name__ == '__main__':
    main()
