"""Check lazy finite token-flow proofs by streaming every original column."""
from collections import defaultdict
from fractions import Fraction

from finite_token_cut_checker import (
    checked_bounds, cut_row, fields, integer, master_rows, positive_rational,
    require, validate_problem,
)


class Work:
    def __init__(self, limit=20_000_000):
        self.remaining = limit

    def take(self, amount=1):
        self.remaining -= amount
        require(self.remaining >= 0, 'lazy checker work limit')


def projection(problem, controls, finite):
    require(type(controls) is list, 'invalid controls')
    previous = -1
    for place in controls:
        integer(place, previous + 1, len(problem['places']) - 1)
        require(finite[place] is not None and finite[place] <= 2**64 - 1,
                'selected coordinate has no representable certified bound')
        previous = place
    coordinates = {place: i for i, place in enumerate(controls)}
    projected = []
    for transition in problem['transitions']:
        projected.append(tuple([(coordinates[p], n) for p, n in transition[key]
                                if p in coordinates] for key in ('pre', 'post')))
    return projected


def successor(state, arcs, upper):
    pre, post = arcs
    if any(state[i] < n for i, n in pre):
        return None
    following = list(state)
    for i, n in pre:
        following[i] -= n
    for i, n in post:
        following[i] += n
    if any(n > bound for n, bound in zip(following, upper)):
        return None
    return tuple(following)


def reconstruct_modes(problem, controls, finite, work):
    projected = projection(problem, controls, finite)
    upper = [finite[p] for p in controls]
    initial = tuple(problem['initial'][p] for p in controls)
    require(all(n <= bound for n, bound in zip(initial, upper)), 'initial exceeds bound')
    modes, indices = [initial], {initial: 0}
    changing_edges = 0
    source = 0
    while source < len(modes):
        for arcs in projected:
            work.take()
            following = successor(modes[source], arcs, upper)
            if following is None or following == modes[source]:
                continue
            changing_edges += 1
            require(changing_edges <= 8192, 'nonstutter edge limit')
            if following not in indices:
                require(len(modes) < 4096, 'finite mode limit')
                indices[following] = len(modes)
                modes.append(following)
        source += 1
    return modes, indices, projected


def edge_coefficient(problem, controls, modes, finite, source, target,
                     transition, cuts, weights, mode_offset, cut_offset, work):
    tr = problem['transitions'][transition]
    delta = defaultdict(int)
    for p, n in tr['pre']:
        delta[p] -= n
    for p, n in tr['post']:
        delta[p] += n
    work.take(len(tr['pre']) + len(tr['post']) + len(cuts))
    value = sum((weights[2*p] - weights[2*p+1]) * n for p, n in delta.items())
    value += weights[mode_offset+2*source+1] - weights[mode_offset+2*source]
    value -= weights[mode_offset+2*target+1] - weights[mode_offset+2*target]
    pre = dict(tr['pre'])
    coordinates = {p: i for i, p in enumerate(controls)}
    for index, cut in enumerate(cuts):
        p, inside = cut['place'], set(cut['modes'])
        enters, leaves = target in inside, source in inside
        if enters and leaves:
            coefficient = -delta[p]
        elif enters:
            lower = modes[source][coordinates[p]] if p in coordinates else pre.get(p, 0)
            coefficient = -lower - delta[p]
        elif leaves:
            if p in coordinates:
                coefficient = modes[source][coordinates[p]]
            else:
                require(finite[p] is not None, 'cut crosses unbounded outgoing edge')
                coefficient = max(finite[p], pre.get(p, 0))
        else:
            coefficient = 0
        value += weights[cut_offset+index] * coefficient
    return value


def verify_lazy_token_cut(problem, proof, max_work=20_000_000):
    validate_problem(problem)
    fields(proof, ('kind', 'controls', 'bounds', 'terminals'))
    require(proof['kind'] == 'lazy-finite-token-cut-v1', 'wrong proof kind')
    finite = checked_bounds(problem, proof['bounds'])
    controls = proof['controls']
    work = Work(max_work)
    modes, indices, projected = reconstruct_modes(problem, controls, finite, work)
    require(type(proof['terminals']) is list and len(proof['terminals']) == len(modes),
            'incomplete terminal coverage')
    upper = [finite[p] for p in controls]
    for terminal, leaf in enumerate(proof['terminals']):
        fields(leaf, ('cuts', 'multipliers'))
        require(type(leaf['cuts']) is list and type(leaf['multipliers']) is list,
                'invalid terminal proof')
        rows = list(master_rows(problem, controls, modes, [], terminal))
        cut_offset = len(rows)
        mode_offset = cut_offset - 2 * len(modes)
        rows.extend(cut_row(problem, controls, modes, [], terminal, finite, cut)
                    for cut in leaf['cuts'])
        weights = [Fraction(0)] * len(rows)
        lhs, rhs, previous = defaultdict(Fraction), Fraction(0), -1
        for entry in leaf['multipliers']:
            require(type(entry) is list and len(entry) == 2, 'invalid multiplier')
            index, raw = entry
            integer(index, previous + 1, len(rows) - 1)
            weight = positive_rational(raw)
            previous = index
            weights[index] = weight
            terms, bound = rows[index]
            for variable, coefficient in terms:
                lhs[variable] += weight * coefficient
            rhs += weight * bound
        require(rhs > 0 and all(value <= 0 for value in lhs.values()),
                'invalid marking-column contradiction')
        for source, state in enumerate(modes):
            for transition, arcs in enumerate(projected):
                work.take()
                following = successor(state, arcs, upper)
                if following is None:
                    continue
                require(following in indices, 'incomplete finite graph')
                coefficient = edge_coefficient(
                    problem, controls, modes, finite, source, indices[following],
                    transition, leaf['cuts'], weights, mode_offset, cut_offset, work)
                require(coefficient <= 0, 'original edge invalidates Farkas contradiction')
    return 'python-lazy-finite-token-cut'
