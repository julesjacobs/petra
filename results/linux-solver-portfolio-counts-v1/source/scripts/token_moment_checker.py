#!/usr/bin/env python3
"""Independent exact checking of token-moment-v1 negative certificates."""
import argparse
import collections
from fractions import Fraction
import json


def validate_problem(problem):
    size = len(problem['places'])
    assert len(problem['initial']) == size
    assert all(type(x) is int and 0 <= x < 2**64 for x in problem['initial'])
    for transition in problem['transitions']:
        for side in ('pre', 'post'):
            seen = set()
            for place, weight in transition[side]:
                assert type(place) is int and 0 <= place < size and place not in seen
                assert type(weight) is int and 0 < weight < 2**64
                seen.add(place)
    for constraint in problem['target']:
        assert len(constraint['coefficients']) == size
        assert all(type(a) is int and -2**63 <= a < 2**63 for a in constraint['coefficients'])
        assert type(constraint['bound']) is int and -2**63 <= constraint['bound'] < 2**63
        assert type(constraint['equality']) is bool


def reconstruct_control(problem, controls):
    validate_problem(problem)
    assert controls and controls == sorted(set(controls))
    assert all(type(p) is int and 0 <= p < len(problem['places']) for p in controls)
    selected = set(controls)
    assert sum(problem['initial'][p] for p in controls) == 1
    projected = []
    for t, transition in enumerate(problem['transitions']):
        pre = {p: w for p, w in transition['pre'] if p in selected}
        post = {p: w for p, w in transition['post'] if p in selected}
        assert sum(pre.values()) == sum(post.values())
        projected.append((t, pre, post))
    # The wire format orders control-independent firings before other firings.
    ordered = sorted(projected, key=lambda item: (bool(item[1]), item[0]))
    modes = [next(p for p in controls if problem['initial'][p] == 1)]
    mode_indices = {modes[0]: 0}
    edges = []
    source = 0
    while source < len(modes):
        marking = {p: int(p == modes[source]) for p in controls}
        for t, pre, post in ordered:
            if not all(marking[p] >= w for p, w in pre.items()):
                continue
            successor = {p: marking[p] - pre.get(p, 0) + post.get(p, 0) for p in controls}
            assert sum(successor.values()) == 1 and all(x >= 0 for x in successor.values())
            occupied = next(p for p in controls if successor[p] == 1)
            if occupied not in mode_indices:
                mode_indices[occupied] = len(modes)
                modes.append(occupied)
            edges.append((source, mode_indices[occupied], t))
        source += 1
    return modes, edges


def relaxation_rows(problem, controls, modes, edges, terminal):
    """Rows mean sum(coefficients * nonnegative variables) >= bound.

    Symbolic variable names keep the checker independent of Rust column offsets.
    """
    size = len(problem['places'])
    effects = []
    for transition in problem['transitions']:
        pre, post = dict(transition['pre']), dict(transition['post'])
        effects.append([post.get(p, 0) - pre.get(p, 0) for p in range(size)])

    def equality(terms, bound):
        yield [(variable, -coefficient) for variable, coefficient in terms], -bound
        yield terms, bound

    for p in range(size):
        terms = [(('final', p), 1)]
        terms += [(('count', e), -effects[t][p]) for e, (_, _, t) in enumerate(edges)]
        yield from equality(terms, problem['initial'][p])
    for p in controls:
        yield from equality([(('final', p), 1)], int(p == modes[terminal]))
    for constraint in problem['target']:
        terms = [(('final', p), a) for p, a in enumerate(constraint['coefficients'])]
        if constraint['equality']:
            yield from equality(terms, constraint['bound'])
        else:
            yield terms, constraint['bound']
    for q in range(len(modes)):
        incidence = [int(source == q) - int(destination == q) for source, destination, _ in edges]
        yield from equality([(('count', e), a) for e, a in enumerate(incidence)],
                            int(q == 0) - int(q == terminal))
        for p in range(size):
            terms = [(('final', p), int(q == terminal))]
            terms += [(('moment', e, p), a) for e, a in enumerate(incidence)]
            terms += [(('count', e), -effects[t][p])
                      for e, (_, destination, t) in enumerate(edges) if destination == q]
            yield from equality(terms, problem['initial'][p] if q == 0 else 0)
    for e, (source, _, t) in enumerate(edges):
        for p, weight in problem['transitions'][t]['pre']:
            yield [(('moment', e, p), 1), (('count', e), -weight)], 0
        for p in controls:
            yield from equality([(('moment', e, p), 1), (('count', e), -int(modes[source] == p))], 0)


def verify_token_moment(problem, proof):
    assert set(proof) == {'kind', 'controls', 'terminals'}
    assert proof['kind'] == 'token-moment-v1'
    controls = proof['controls']
    modes, edges = reconstruct_control(problem, controls)
    assert len(proof['terminals']) == len(modes)
    for terminal, multipliers in enumerate(proof['terminals']):
        weights = {}
        previous = -1
        for index, raw in multipliers:
            assert type(index) is int and index > previous
            assert type(raw) is str
            weight = Fraction(raw)
            assert weight > 0
            weights[index] = weight
            previous = index
        lhs = collections.defaultdict(Fraction)
        rhs = Fraction(0)
        for index, (terms, bound) in enumerate(relaxation_rows(problem, controls, modes, edges, terminal)):
            weight = weights.pop(index, None)
            if weight is None:
                continue
            for variable, coefficient in terms:
                lhs[variable] += weight * coefficient
            rhs += weight * bound
        assert not weights, 'certificate refers to a nonexistent row'
        assert rhs > 0 and all(a <= 0 for a in lhs.values()), 'invalid Farkas contradiction'
    return 'python-token-moment'


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
    result = verify_token_moment(problem, proof)
    modes, edges = reconstruct_control(problem, proof['controls'])
    print(json.dumps(dict(checker=result, terminals=len(modes), edges=len(edges), verified=True)))


if __name__ == '__main__':
    main()
