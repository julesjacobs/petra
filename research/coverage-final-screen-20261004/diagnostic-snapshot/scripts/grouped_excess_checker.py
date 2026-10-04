"""Independent exact checking of grouped token-excess invariants."""
import time


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify(problem, proof, deadline=None, max_work=20_000_000):
    deadline = time.monotonic() + 60 if deadline is None else deadline
    work = 0

    def charge(n=1):
        nonlocal work
        work += n
        if work > max_work or time.monotonic() >= deadline:
            raise TimeoutError('grouped excess verification limit')

    def integer(x, lower, upper):
        return type(x) is int and lower <= x < upper

    require(type(problem) is dict, 'invalid problem')
    require(type(problem.get('places')) is list, 'invalid places')
    n = len(problem['places'])
    charge(n + 1)
    initial = problem.get('initial')
    require(type(initial) is list and len(initial) == n, 'invalid initial dimension')
    require(all(integer(x, 0, 2**64) for x in initial), 'invalid initial value')
    require(type(problem.get('transitions')) is list, 'invalid transitions')
    require(type(problem.get('target')) is list, 'invalid target')
    for row in problem['target']:
        charge(n + 1)
        require(type(row) is dict and type(row.get('coefficients')) is list
                and len(row['coefficients']) == n, 'invalid target dimension')
        require(all(integer(a, -2**63, 2**63) for a in row['coefficients'])
                and integer(row.get('bound'), -2**63, 2**63)
                and type(row.get('equality')) is bool, 'invalid target arithmetic')
    require(type(proof) is dict and set(proof) ==
            {'kind', 'groups', 'thresholds', 'target_row', 'sign'}, 'invalid proof fields')
    require(proof['kind'] == 'grouped-excess-v1', 'invalid proof kind')
    groups, thresholds = proof['groups'], proof['thresholds']
    require(type(groups) is list and type(thresholds) is list
            and len(groups) == len(thresholds), 'invalid group dimensions')
    require(all(integer(k, 0, 2**64) for k in thresholds), 'invalid thresholds')
    owner = [None] * n
    for g, group in enumerate(groups):
        require(type(group) is list and group, 'empty or invalid group')
        previous = -1
        charge(len(group) + 1)
        for place in group:
            require(integer(place, 0, n) and place > previous
                    and owner[place] is None, 'invalid group partition')
            owner[place] = g
            previous = place
    require(all(g is not None for g in owner), 'group partition omits a place')

    for transition in problem['transitions']:
        charge()
        require(type(transition) is dict, 'invalid transition')
        totals = [{}, {}]
        for side, field in enumerate(['pre', 'post']):
            arcs = transition.get(field)
            require(type(arcs) is list, 'invalid arcs')
            charge(len(arcs))
            seen = set()
            for arc in arcs:
                require(type(arc) in (list, tuple) and len(arc) == 2, 'invalid arc')
                place, weight = arc
                require(integer(place, 0, n) and place not in seen
                        and integer(weight, 1, 2**64), 'invalid arc value')
                seen.add(place)
                g = owner[place]
                totals[side][g] = totals[side].get(g, 0) + weight
        change_bound = 0
        for g in totals[0].keys() | totals[1].keys():
            charge()
            pre = totals[0].get(g, 0)
            delta = totals[1].get(g, 0) - pre
            threshold = thresholds[g]
            # A piecewise-linear function attains its maximum at a breakpoint
            # or on the constant tail; include the enabling boundary as well.
            candidates = {pre, max(pre, threshold), max(pre, threshold - delta)}
            change_bound += max(max(z + delta - threshold, 0) - max(z - threshold, 0)
                                for z in candidates)
        require(change_bound <= 0, 'grouped excess can increase on a transition')

    charge(n + len(groups))
    masses = [sum(initial[p] for p in group) for group in groups]
    budget = sum(max(mass - k, 0) for mass, k in zip(masses, thresholds))
    row_index, sign = proof['target_row'], proof['sign']
    require(integer(row_index, 0, len(problem['target'])), 'invalid target row')
    require(type(sign) is int and sign in (-1, 1), 'invalid target sign')
    row = problem['target'][row_index]
    require(sign == 1 or row['equality'], 'negated inequality')
    coefficients = [max([0] + [sign * row['coefficients'][p] for p in group])
                    for group in groups]
    upper = sum(a * k for a, k in zip(coefficients, thresholds))
    upper += budget * max(coefficients, default=0)
    require(upper < sign * row['bound'], 'grouped excess does not exclude target')
    charge()
    return 'python-grouped-excess'
