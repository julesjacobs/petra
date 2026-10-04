"""Check the all-ones target-path bound and reconstruct its slack-place net.

The total token count must never decrease. Unary target bounds then bound every
prefix of a successful execution, even when the original net is unbounded.
"""
import math
import time

DEFAULT_MAX_WORK = 20_000_000


def require(condition, message):
    if not condition:
        raise ValueError(message)


class Budget:
    def __init__(self, deadline, max_work):
        require(type(deadline) in (int, float) and math.isfinite(deadline), 'invalid deadline')
        require(type(max_work) is int and max_work >= 0, 'invalid work limit')
        self.deadline, self.remaining = deadline, max_work

    def tick(self, work=1):
        self.remaining -= work
        if self.remaining < 0 or time.monotonic() >= self.deadline:
            raise TimeoutError('target-path potential verification limit')


def integer(value, low, high):
    require(type(value) is int and low <= value < high, 'invalid integer')


def fields(value, expected):
    require(type(value) is dict and set(value) == set(expected), 'invalid fields')


def _reconstruct(problem, budget, infeasible):
    fields(problem, ('places', 'initial', 'transitions', 'target'))
    places, initial = problem['places'], problem['initial']
    require(type(places) is list and type(initial) is list and len(initial) == len(places),
            'invalid marking dimension')
    n = len(places)
    require(n > 0, 'empty potential support')
    budget.tick(n)
    names = set()
    initial_total = 0
    for name, tokens in zip(places, initial):
        budget.tick()
        require(type(name) is str, 'invalid place name')
        budget.tick(len(name))
        names.add(name)
        integer(tokens, 0, 2**64)
        initial_total += tokens
    integer(initial_total, 0, 2**127)

    require(type(problem['target']) is list, 'invalid target')
    bounds = [None] * n
    target = []
    for row in problem['target']:
        budget.tick()
        fields(row, ('coefficients', 'bound', 'equality'))
        coefficients, rhs = row['coefficients'], row['bound']
        require(type(coefficients) is list and len(coefficients) == n, 'target dimension mismatch')
        integer(rhs, -2**63, 2**63)
        require(type(row['equality']) is bool, 'invalid equality flag')
        support = []
        for i, coefficient in enumerate(coefficients):
            budget.tick()
            integer(coefficient, -2**63, 2**63)
            if coefficient:
                support.append((i, coefficient))
        if len(support) == 1:
            i, coefficient = support[0]
            if row['equality'] or coefficient < 0:
                bound = rhs // coefficient
                bounds[i] = bound if bounds[i] is None else min(bounds[i], bound)
        target.append(dict(coefficients=coefficients + [0], bound=rhs, equality=row['equality']))
    require(all(bound is not None for bound in bounds), 'missing target upper bound')
    bound = sum(bounds)
    integer(bound, -2**127, 2**127)

    require(type(problem['transitions']) is list, 'invalid transitions')
    transitions, growth = [], False
    for transition in problem['transitions']:
        budget.tick()
        fields(transition, ('name', 'pre', 'post'))
        require(type(transition['name']) is str, 'invalid transition name')
        budget.tick(len(transition['name']))
        arcs, totals = {}, {}
        for side in ('pre', 'post'):
            require(type(transition[side]) is list, 'invalid arcs')
            seen, copied, total = set(), [], 0
            for arc in transition[side]:
                budget.tick()
                require(type(arc) is list and len(arc) == 2, 'invalid arc')
                i, weight = arc
                integer(i, 0, n)
                integer(weight, 1, 2**64)
                require(i not in seen, 'duplicate arc')
                seen.add(i)
                copied.append([i, weight])
                total += weight
            integer(total, 0, 2**127)
            arcs[side], totals[side] = copied, total
        delta = totals['post'] - totals['pre']
        require(delta >= 0, 'total tokens can decrease')
        if delta:
            growth = True
            if not infeasible:
                integer(delta, 1, 2**64)
            arcs['pre'].append([n, delta])
        transitions.append(dict(name=transition['name'], **arcs))
    budget.tick()
    if infeasible:
        require(initial_total > bound, 'initial total does not exceed target bound')
        return None
    require(initial_total <= bound, 'negative initial slack')
    require(growth, 'potential adds no guard')
    slack = bound - initial_total
    integer(slack, 0, 2**64)
    name = '__target_path_slack'
    while name in names:
        budget.tick(len(name))
        name += '_'
    budget.tick(n + len(name))
    return dict(places=places + [name], initial=initial + [slack],
                transitions=transitions, target=target)


def augment(problem, deadline=None, max_work=DEFAULT_MAX_WORK):
    deadline = time.monotonic() + 60 if deadline is None else deadline
    return _reconstruct(problem, Budget(deadline, max_work), infeasible=False)


def verify(problem, proof, check_inner=None, deadline=None, max_work=DEFAULT_MAX_WORK):
    deadline = time.monotonic() + 60 if deadline is None else deadline
    budget = Budget(deadline, max_work)
    budget.tick()
    require(type(proof) is dict, 'invalid target-path potential proof')
    kind = proof.get('kind')
    require(type(kind) is str and kind in (
        'target-path-potential-v1', 'target-path-potential-infeasible-v1'), 'invalid proof kind')
    infeasible = kind == 'target-path-potential-infeasible-v1'
    fields(proof, ('kind',) if infeasible else ('kind', 'inner'))
    if not infeasible:
        require(type(proof['inner']) is dict and callable(check_inner), 'invalid inner proof')
    augmented = _reconstruct(problem, budget, infeasible)
    if infeasible:
        return 'python-target-path-potential-infeasible'
    checked = check_inner(augmented, proof['inner'])
    budget.tick()
    require(type(checked) is str and checked.startswith('python-'), 'inner proof has no independent verification')
    return 'python-target-path-potential'
