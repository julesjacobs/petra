"""Check target-zero trap proofs against the original weighted net.

Every target marking empties the certified trap. Once marked, a trap stays
marked, so a successful run from an empty trap cannot fire a transition that
produces into it. Removing those transitions and the trap coordinates therefore
preserves every successful run. Inner unreachability is checked independently.
"""
import math
import time

DEFAULT_MAX_WORK = 20_000_000


def require(condition, message):
    if not condition:
        raise ValueError(message)


class Budget:
    def __init__(self, deadline, max_work):
        require(type(deadline) in (int, float) and math.isfinite(deadline),
                'invalid target-zero trap deadline')
        require(type(max_work) is int and max_work >= 0,
                'invalid target-zero trap work limit')
        self.deadline = deadline
        self.remaining = max_work

    def tick(self):
        self.remaining -= 1
        if self.remaining < 0:
            raise TimeoutError('target-zero trap verification work limit')
        if time.monotonic() >= self.deadline:
            raise TimeoutError('target-zero trap verification deadline')


def _check(problem, trap, budget, marked):
    budget.tick()
    require(type(problem) is dict and len(problem) == 4 and set(problem) == {'places', 'initial', 'transitions', 'target'},
            'invalid original problem fields')
    require(type(problem['places']) is list, 'invalid original places')
    for name in problem['places']:
        budget.tick()
        require(type(name) is str, 'invalid place name')
    n = len(problem['places'])
    require(type(problem['initial']) is list and len(problem['initial']) == n,
            'initial dimension mismatch')
    for count in problem['initial']:
        budget.tick()
        require(type(count) is int and 0 <= count < 2**64, 'invalid initial marking')
    require(type(trap) is list, 'invalid trap indices')
    chosen = set()
    previous = -1
    initially_marked = False
    for place in trap:
        budget.tick()
        require(type(place) is int and previous < place < n,
                'trap indices must be ordered, unique original indices')
        previous = place
        chosen.add(place)
        initially_marked |= problem['initial'][place] != 0

    places, initial, ids = [], [], {}
    for place, name in enumerate(problem['places']):
        budget.tick()
        if place not in chosen:
            ids[place] = len(places)
            places.append(name)
            initial.append(problem['initial'][place])

    require(type(problem['target']) is list, 'invalid original target')
    forced_zero = set()
    target = []
    for constraint in problem['target']:
        budget.tick()
        require(type(constraint) is dict and len(constraint) == 3 and set(constraint) == {'coefficients', 'bound', 'equality'},
                'invalid target constraint fields')
        coefficients, bound, equality = (constraint[k] for k in ('coefficients', 'bound', 'equality'))
        require(type(coefficients) is list and len(coefficients) == n, 'target dimension mismatch')
        require(type(bound) is int and -2**63 <= bound < 2**63, 'invalid target bound')
        require(type(equality) is bool, 'invalid equality flag')
        positive, negative = False, False
        support, projected = [], []
        for place, coefficient in enumerate(coefficients):
            budget.tick()
            require(type(coefficient) is int and -2**63 <= coefficient < 2**63,
                    'invalid target coefficient')
            positive |= coefficient > 0
            negative |= coefficient < 0
            if coefficient:
                support.append(place)
            if place in ids:
                projected.append(coefficient)
        if bound == 0 and (not positive or (equality and not negative)):
            for place in support:
                budget.tick()
                forced_zero.add(place)
        target.append(dict(coefficients=projected, bound=bound, equality=equality))
    for place in trap:
        budget.tick()
        require(place in forced_zero, 'trap coordinate is not forced zero by the target')

    require(type(problem['transitions']) is list, 'invalid original transitions')
    transitions = []
    for transition in problem['transitions']:
        budget.tick()
        require(type(transition) is dict and len(transition) == 3 and set(transition) == {'name', 'pre', 'post'},
                'invalid original transition fields')
        require(type(transition['name']) is str, 'invalid transition name')
        touches, arcs = {}, {}
        for side in ('pre', 'post'):
            require(type(transition[side]) is list, 'invalid original arcs')
            seen, projected = set(), []
            touches[side] = False
            for arc in transition[side]:
                budget.tick()
                require(type(arc) is list and len(arc) == 2, 'invalid original arc')
                place, weight = arc
                require(type(place) is int and 0 <= place < n and place not in seen,
                        'invalid or duplicate original arc place')
                require(type(weight) is int and 0 < weight < 2**64, 'invalid original arc weight')
                seen.add(place)
                touches[side] |= place in chosen
                if place in ids:
                    projected.append([ids[place], weight])
            arcs[side] = projected
        require(not touches['pre'] or touches['post'], 'trap has a consuming transition without a producing arc')
        if not touches['post']:
            transitions.append(dict(name=transition['name'], **arcs))
    require(initially_marked == marked,
            'trap must be initially marked' if marked else 'trap must be initially empty')
    budget.tick()
    return dict(places=places, initial=initial, transitions=transitions, target=target)


def project(problem, trap, deadline=None, max_work=DEFAULT_MAX_WORK):
    if deadline is None:
        deadline = time.monotonic() + 60
    return _check(problem, trap, Budget(deadline, max_work), marked=False)


def verify(problem, proof, check_inner=None, deadline=None, max_work=DEFAULT_MAX_WORK):
    if deadline is None:
        deadline = time.monotonic() + 60
    budget = Budget(deadline, max_work)
    budget.tick()
    require(type(proof) is dict, 'invalid target-zero trap proof')
    kind = proof.get('kind')
    require(type(kind) is str and kind in ('target-zero-trap-v1', 'target-zero-trap-marked-v1'),
            'invalid target-zero trap proof kind')
    marked = kind == 'target-zero-trap-marked-v1'
    fields = {'kind', 'trap'} if marked else {'kind', 'trap', 'inner'}
    require(len(proof) == len(fields) and set(proof) == fields,
            'invalid target-zero trap proof fields')
    if not marked:
        require(type(proof['inner']) is dict and callable(check_inner), 'invalid target-zero trap inner proof')
    reduced = _check(problem, proof['trap'], budget, marked)
    if marked:
        return 'python-target-zero-trap-marked'
    result = check_inner(reduced, proof['inner'])
    budget.tick()
    require(type(result) is str and result.startswith('python-'),
            'inner proof has no independent verification')
    return 'python-target-zero-trap'
