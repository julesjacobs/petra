#!/usr/bin/env python3
"""Independent exact checking of finite-token-cut-v1 certificates."""
import argparse
from collections import defaultdict
from fractions import Fraction
import json


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fields(value, names):
    require(type(value) is dict and set(value) == set(names), 'invalid object fields')


def integer(value, lower, upper):
    require(type(value) is int and lower <= value <= upper, 'invalid integer')


def validate_problem(problem):
    fields(problem, ('places', 'initial', 'transitions', 'target'))
    require(type(problem['places']) is list and all(type(p) is str for p in problem['places']),
            'invalid place names')
    size = len(problem['places'])
    require(type(problem['initial']) is list and len(problem['initial']) == size,
            'invalid initial marking')
    for value in problem['initial']:
        integer(value, 0, 2**64 - 1)
    require(type(problem['transitions']) is list, 'invalid transitions')
    for transition in problem['transitions']:
        fields(transition, ('name', 'pre', 'post'))
        require(type(transition['name']) is str, 'invalid transition name')
        for key in ('pre', 'post'):
            require(type(transition[key]) is list, 'invalid arcs')
            seen = set()
            for arc in transition[key]:
                require(type(arc) is list and len(arc) == 2, 'invalid arc')
                place, weight = arc
                integer(place, 0, size - 1)
                integer(weight, 1, 2**64 - 1)
                require(place not in seen, 'duplicate arc')
                seen.add(place)
    require(type(problem['target']) is list, 'invalid target')
    for constraint in problem['target']:
        fields(constraint, ('coefficients', 'bound', 'equality'))
        require(type(constraint['coefficients']) is list
                and len(constraint['coefficients']) == size, 'invalid target dimension')
        require(type(constraint['equality']) is bool, 'invalid equality flag')
        for value in constraint['coefficients'] + [constraint['bound']]:
            integer(value, -2**63, 2**63 - 1)


def positive_rational(raw):
    require(type(raw) is str, 'rational must be a string')
    value = Fraction(raw)
    require(value > 0, 'nonpositive rational')
    return value


def checked_bounds(problem, certificate):
    fields(certificate, ('kind', 'potentials'))
    require(certificate['kind'] == 'place-bounds-v1', 'wrong bound certificate kind')
    require(type(certificate['potentials']) is list, 'invalid potentials')
    finite = [None] * len(problem['places'])
    for potential in certificate['potentials']:
        fields(potential, ('weights',))
        require(type(potential['weights']) is list and potential['weights'], 'empty potential')
        weights = {}
        previous = -1
        for entry in potential['weights']:
            require(type(entry) is list and len(entry) == 2, 'invalid potential entry')
            place, raw = entry
            integer(place, previous + 1, len(finite) - 1)
            weights[place] = positive_rational(raw)
            previous = place
        for transition in problem['transitions']:
            total = lambda arcs: sum(weights.get(p, 0) * n for p, n in arcs)
            require(total(transition['post']) <= total(transition['pre']),
                    'potential increases on original transition')
        mass = sum(weight * problem['initial'][p] for p, weight in weights.items())
        for place, weight in weights.items():
            ratio = mass / weight
            bound = ratio.numerator // ratio.denominator
            if finite[place] is None or bound < finite[place]:
                finite[place] = bound
    return finite


def reconstruct(problem, controls, finite):
    require(type(controls) is list, 'invalid controls')
    previous = -1
    for place in controls:
        integer(place, previous + 1, len(problem['places']) - 1)
        require(finite[place] is not None and finite[place] <= 2**64 - 1,
                'selected coordinate has no representable certified bound')
        previous = place
    initial = tuple(problem['initial'][p] for p in controls)
    require(all(v <= finite[p] for p, v in zip(controls, initial)), 'initial exceeds bound')
    projected = []
    for transition in problem['transitions']:
        pre, post = dict(transition['pre']), dict(transition['post'])
        projected.append(([pre.get(p, 0) for p in controls],
                          [post.get(p, 0) for p in controls]))
    modes, indices, edges = [initial], {initial: 0}, []
    source = 0
    while source < len(modes):
        for transition, (pre, post) in enumerate(projected):
            state = modes[source]
            if any(v < a for v, a in zip(state, pre)):
                continue
            successor = tuple(v - a + b for v, a, b in zip(state, pre, post))
            if any(v > finite[p] for p, v in zip(controls, successor)):
                continue
            require(len(edges) < 8192, 'finite graph edge limit')
            if successor not in indices:
                require(len(modes) < 4096, 'finite graph mode limit')
                indices[successor] = len(modes)
                modes.append(successor)
            edges.append((source, indices[successor], transition))
        source += 1
    return modes, edges


def equality(terms, bound):
    yield [(variable, -value) for variable, value in terms], -bound
    yield terms, bound


def master_rows(problem, controls, modes, edges, terminal):
    incidence = [[] for _ in problem['places']]
    conservation = [[] for _ in modes]
    for edge, (source, target, transition) in enumerate(edges):
        for p, weight in problem['transitions'][transition]['pre']:
            incidence[p].append((('count', edge), weight))
        for p, weight in problem['transitions'][transition]['post']:
            incidence[p].append((('count', edge), -weight))
        conservation[source].append((('count', edge), 1))
        conservation[target].append((('count', edge), -1))
    for p, terms in enumerate(incidence):
        yield from equality(terms + [(('final', p), 1)], problem['initial'][p])
    for p, value in zip(controls, modes[terminal]):
        yield from equality([(('final', p), 1)], value)
    for constraint in problem['target']:
        terms = [(('final', p), value) for p, value in enumerate(constraint['coefficients']) if value]
        if constraint['equality']:
            yield from equality(terms, constraint['bound'])
        else:
            yield terms, constraint['bound']
    for mode, terms in enumerate(conservation):
        yield from equality(terms, int(mode == 0) - int(mode == terminal))


def cut_row(problem, controls, modes, edges, terminal, finite, cut):
    fields(cut, ('place', 'modes'))
    place, subset = cut['place'], cut['modes']
    integer(place, 0, len(problem['places']) - 1)
    require(type(subset) is list, 'invalid mode subset')
    previous = -1
    for mode in subset:
        integer(mode, previous + 1, len(modes) - 1)
        previous = mode
    inside = set(subset)
    coefficients = defaultdict(int)
    if terminal in inside:
        coefficients['final', place] += 1
    coordinate = controls.index(place) if place in controls else None
    for edge, (source, target, transition) in enumerate(edges):
        tr = problem['transitions'][transition]
        pre, post = dict(tr['pre']).get(place, 0), dict(tr['post']).get(place, 0)
        lower = modes[source][coordinate] if coordinate is not None else pre
        upper = lower if coordinate is not None else finite[place]
        if upper is not None:
            upper = max(lower, upper)
        if source in inside:
            coefficients['count', edge] += lower
        if target in inside:
            coefficients['count', edge] -= lower + post - pre
        if source in inside and target not in inside:
            require(upper is not None, 'cut crosses unbounded outgoing edge')
            coefficients['count', edge] += upper - lower
    return list(coefficients.items()), problem['initial'][place] if 0 in inside else 0


def verify_finite_token_cut(problem, proof):
    validate_problem(problem)
    fields(proof, ('kind', 'controls', 'bounds', 'terminals'))
    require(proof['kind'] == 'finite-token-cut-v1', 'wrong proof kind')
    finite = checked_bounds(problem, proof['bounds'])
    controls = proof['controls']
    modes, edges = reconstruct(problem, controls, finite)
    require(type(proof['terminals']) is list and len(proof['terminals']) == len(modes),
            'incomplete terminal coverage')
    for terminal, leaf in enumerate(proof['terminals']):
        fields(leaf, ('cuts', 'multipliers'))
        require(type(leaf['cuts']) is list and type(leaf['multipliers']) is list,
                'invalid terminal proof')
        rows = list(master_rows(problem, controls, modes, edges, terminal))
        rows.extend(cut_row(problem, controls, modes, edges, terminal, finite, cut)
                    for cut in leaf['cuts'])
        lhs, rhs, previous = defaultdict(Fraction), Fraction(0), -1
        for multiplier in leaf['multipliers']:
            require(type(multiplier) is list and len(multiplier) == 2, 'invalid multiplier')
            index, raw = multiplier
            integer(index, previous + 1, len(rows) - 1)
            weight = positive_rational(raw)
            previous = index
            terms, bound = rows[index]
            for variable, coefficient in terms:
                lhs[variable] += weight * coefficient
            rhs += weight * bound
        require(rhs > 0 and all(value <= 0 for value in lhs.values()),
                'invalid Farkas contradiction')
    return 'python-finite-token-cut'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('problem')
    parser.add_argument('certificate')
    args = parser.parse_args()
    with open(args.problem) as stream:
        problem = json.load(stream)
    with open(args.certificate) as stream:
        proof = json.load(stream)
    if 'proof' in proof:
        require(proof.get('verdict') == 'unreachable', 'answer is not negative')
        proof = proof['proof']
    print(json.dumps(dict(checker=verify_finite_token_cut(problem, proof), verified=True)))


if __name__ == '__main__':
    main()
