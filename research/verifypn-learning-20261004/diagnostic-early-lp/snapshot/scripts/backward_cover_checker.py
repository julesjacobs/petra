"""Independent exact checking of predecessor-closed upward marking sets."""
import math
import time


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify(problem, proof, deadline=None, max_work=20_000_000):
    deadline = time.monotonic() + 60 if deadline is None else deadline
    require(type(deadline) in (int, float) and math.isfinite(deadline), 'invalid deadline')
    require(type(max_work) is int and max_work >= 0, 'invalid work budget')
    work = 0

    def charge(n=1):
        nonlocal work
        work += n
        if work > max_work or time.monotonic() >= deadline:
            raise TimeoutError('backward cover verification limit')

    def integer(value, lo, hi):
        return type(value) is int and lo <= value < hi

    require(type(problem) is dict, 'invalid problem')
    places = problem.get('places')
    require(type(places) is list and all(type(p) is str for p in places), 'invalid places')
    n = len(places)
    charge(n+1)
    require(len(set(places)) == n, 'duplicate place name')
    initial = problem.get('initial')
    require(type(initial) is list and len(initial) == n
            and all(integer(v, 0, 2**64) for v in initial), 'invalid initial marking')
    target = problem.get('target')
    require(type(target) is list, 'invalid target')
    for row in target:
        charge(n+1)
        require(type(row) is dict and type(row.get('coefficients')) is list
                and len(row['coefficients']) == n, 'invalid target dimension')
        require(all(integer(v, -2**63, 2**63) for v in row['coefficients'])
                and integer(row.get('bound'), -2**63, 2**63)
                and type(row.get('equality')) is bool, 'invalid target arithmetic')
    require(type(proof) is dict and set(proof) == {'kind', 'requirements', 'basis'}
            and proof['kind'] == 'backward-cover-v1', 'invalid proof fields')
    requirements = proof['requirements']
    require(type(requirements) is list and requirements, 'invalid requirements')
    goal = {}
    for requirement in requirements:
        charge(n+1)
        require(type(requirement) is dict and set(requirement) ==
                {'target_row', 'sign', 'place', 'required'}, 'invalid requirement fields')
        row_index, sign = requirement['target_row'], requirement['sign']
        place, required = requirement['place'], requirement['required']
        require(integer(row_index, 0, len(target)) and integer(place, 0, n)
                and integer(required, 1, 2**64), 'invalid requirement values')
        require(type(sign) is int and sign in (-1, 1), 'invalid requirement sign')
        row = target[row_index]
        require(sign == 1 or row['equality'], 'negated inequality')
        coefficient, bound = sign*row['coefficients'][place], sign*row['bound']
        require(coefficient > 0 and bound > 0, 'nonpositive requirement')
        require(all(p == place or sign*c <= 0 for p, c in enumerate(row['coefficients'])),
                'another positive coefficient')
        require(required == (bound+coefficient-1)//coefficient, 'incorrect requirement')
        goal[place] = max(goal.get(place, 0), required)
    basis = proof['basis']
    require(type(basis) is list and len(basis) <= 20_000, 'invalid basis size')
    lower_bounds = []
    for marking in basis:
        require(type(marking) is list, 'invalid sparse marking')
        charge(len(marking)+1)
        previous, lower = -1, {}
        for pair in marking:
            require(type(pair) is list and len(pair) == 2, 'invalid sparse coordinate')
            place, count = pair
            require(integer(place, 0, n) and place > previous
                    and integer(count, 1, 2**64), 'invalid sparse coordinate values')
            lower[place] = count
            previous = place
        lower_bounds.append(lower)
    transitions = problem.get('transitions')
    require(type(transitions) is list, 'invalid transitions')
    indexed, producers = [], [[] for _ in range(n)]
    nonincreasing = True
    for ti, transition in enumerate(transitions):
        charge()
        require(type(transition) is dict, 'invalid transition')
        sides = []
        for field in ('pre', 'post'):
            arcs = transition.get(field)
            require(type(arcs) is list, 'invalid arcs')
            charge(len(arcs))
            side = {}
            for arc in arcs:
                require(type(arc) in (list, tuple) and len(arc) == 2, 'invalid arc')
                place, weight = arc
                require(integer(place, 0, n) and place not in side
                        and integer(weight, 1, 2**64), 'invalid arc value')
                side[place] = weight
            sides.append(side)
        pre, post = sides
        nonincreasing &= sum(post.values()) <= sum(pre.values())
        for place, count in post.items():
            charge()
            if count > pre.get(place, 0):
                producers[place].append(ti)
        indexed.append((pre, post))
    token_bound = sum(initial) if nonincreasing else None

    def covered(marking):
        for lower in lower_bounds:
            charge()
            dominates = True
            for p, required in lower.items():
                charge()
                if marking.get(p, 0) < required:
                    dominates = False
                    break
            if dominates:
                return True
        return False

    def outside(marking):
        if token_bound is None:
            return False
        charge(len(marking))
        return sum(marking.values()) > token_bound

    charge(n)
    require(not covered({p: v for p, v in enumerate(initial) if v}),
            'initial marking is covered')
    require(outside(goal) or covered(goal), 'basis omits goal')
    for marking in lower_bounds:
        # Other transitions have predecessor >= marking and are already covered.
        candidates = set()
        for place in marking:
            charge(len(producers[place])+1)
            candidates.update(producers[place])
        for ti in candidates:
            charge()
            pre, post = indexed[ti]
            predecessor = {}
            for place in marking.keys() | pre.keys():
                charge()
                count = pre.get(place, 0)+max(marking.get(place, 0)-post.get(place, 0), 0)
                if count:
                    predecessor[place] = count
            require(outside(predecessor) or covered(predecessor), 'basis is not predecessor closed')
    charge()
    return 'python-backward-cover'
