#!/usr/bin/env python3
"""Exact independent checking of bounded-token-cut-v1 certificates."""
import argparse
from fractions import Fraction
import json

from token_cut_checker import verify_terminals
from token_moment_checker import validate_problem


def verify_place_bounds(problem, certificate):
    validate_problem(problem)
    assert set(certificate) == {'kind', 'potentials'}
    assert certificate['kind'] == 'place-bounds-v1'
    assert type(certificate['potentials']) is list
    bounds = [None] * len(problem['places'])
    for potential in certificate['potentials']:
        assert set(potential) == {'weights'}
        assert type(potential['weights']) is list and potential['weights']
        weights = [Fraction(0)] * len(bounds)
        previous = -1
        for place, raw in potential['weights']:
            assert type(place) is int and previous < place < len(bounds)
            assert type(raw) is str
            weight = Fraction(raw)
            assert weight > 0
            weights[place] = weight
            previous = place
        for transition in problem['transitions']:
            change = sum(weights[p]*n for p, n in transition['post'])
            change -= sum(weights[p]*n for p, n in transition['pre'])
            assert change <= 0, 'potential increases on an original transition'
        initial = sum(weight*n for weight, n in zip(weights, problem['initial']))
        for p, weight in enumerate(weights):
            if weight:
                ratio = initial / weight
                bound = ratio.numerator // ratio.denominator
                if bounds[p] is None or bound < bounds[p]:
                    bounds[p] = bound
    return bounds


def verify_bounded_token_cut(problem, proof):
    assert set(proof) == {'kind', 'controls', 'bounds', 'terminals'}
    assert proof['kind'] == 'bounded-token-cut-v1'
    bounds = verify_place_bounds(problem, proof['bounds'])
    verify_terminals(problem, proof, bounds)
    return 'python-bounded-token-cut'


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
    print(json.dumps(dict(checker=verify_bounded_token_cut(problem, proof), verified=True)))


if __name__ == '__main__':
    main()
