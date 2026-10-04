"""Check relevance reduction against original arcs before checking its inner proof.

Skipping an omitted transition increases retained coordinates relative to the
original run, without changing target coordinates. Every retained guard is
preserved, so projected retained transitions simulate the original run and
preserve its final target value. Reduced unreachability implies original
unreachability.
"""
import math
import time


DEFAULT_MAX_WORK = 20_000_000


def require(condition, message):
    if not condition:
        raise ValueError(message)


class Budget:
    def __init__(self, deadline, max_work):
        require(type(deadline) in (int, float) and math.isfinite(deadline), 'invalid relevance deadline')
        require(type(max_work) is int and max_work >= 0, 'invalid relevance work limit')
        self.deadline = deadline
        self.remaining = max_work

    def tick(self, amount=1):
        self.remaining -= amount
        if self.remaining < 0:
            raise TimeoutError('relevance verification work limit')
        if time.monotonic() >= self.deadline:
            raise TimeoutError('relevance verification deadline')


def _project(problem, places, transitions, budget):
    budget.tick()
    require(type(problem) is dict and all(k in problem for k in ('places', 'initial', 'transitions', 'target')),
            'invalid original problem')
    require(type(problem['places']) is list, 'invalid original places')
    for name in problem['places']:
        budget.tick()
        require(type(name) is str, 'invalid place name')
    n = len(problem['places'])
    require(type(problem['initial']) is list and len(problem['initial']) == n, 'initial dimension mismatch')
    for value in problem['initial']:
        budget.tick()
        require(type(value) is int and 0 <= value < 2**64, 'invalid initial marking')
    require(type(problem['transitions']) is list, 'invalid original transitions')

    def mapping(indices, size):
        require(type(indices) is list, 'invalid relevance mapping')
        previous = -1
        result = {}
        for index in indices:
            budget.tick()
            require(type(index) is int and previous < index < size, 'relevance mappings must be ordered, unique original indices')
            result[index] = len(result)
            previous = index
        return result

    place_ids = mapping(places, n)
    transition_ids = mapping(transitions, len(problem['transitions']))
    require(type(problem['target']) is list, 'invalid original target')
    target_support = set()
    target = []
    for constraint in problem['target']:
        budget.tick()
        require(type(constraint) is dict and all(k in constraint for k in ('coefficients', 'bound', 'equality')),
                'invalid target constraint')
        coefficients = constraint['coefficients']
        require(type(coefficients) is list and len(coefficients) == n, 'target dimension mismatch')
        for place, coefficient in enumerate(coefficients):
            budget.tick()
            require(type(coefficient) is int and -2**63 <= coefficient < 2**63, 'invalid target coefficient')
            if coefficient:
                require(place in place_ids, 'omitted target support')
                target_support.add(place)
        require(type(constraint['bound']) is int and -2**63 <= constraint['bound'] < 2**63, 'invalid target bound')
        require(type(constraint['equality']) is bool, 'invalid equality flag')
        target.append(dict(coefficients=[coefficients[p] for p in places],
                           bound=constraint['bound'], equality=constraint['equality']))
    reduced_transitions = []
    for index, transition in enumerate(problem['transitions']):
        budget.tick()
        require(type(transition) is dict and all(k in transition for k in ('name', 'pre', 'post')),
                'invalid original transition')
        require(type(transition['name']) is str, 'invalid transition name')
        retained = index in transition_ids
        delta = {}
        arcs = {}
        for field, sign in (('pre', -1), ('post', 1)):
            require(type(transition[field]) is list, 'invalid original arcs')
            seen = set()
            projected = []
            for term in transition[field]:
                budget.tick()
                require(type(term) is list and len(term) == 2, 'invalid original arc')
                place, weight = term
                require(type(place) is int and 0 <= place < n and place not in seen, 'invalid or duplicate original arc place')
                require(type(weight) is int and 0 < weight < 2**64, 'invalid original arc weight')
                seen.add(place)
                if retained and field == 'pre':
                    require(place in place_ids, 'omitted retained-transition guard')
                if place in place_ids:
                    delta[place] = delta.get(place, 0) + sign*weight
                    projected.append([place_ids[place], weight])
            arcs[field] = projected
        if retained:
            reduced_transitions.append(dict(name=transition['name'], **arcs))
        else:
            for place, effect in delta.items():
                budget.tick()
                require(effect <= 0, 'omitted transition produces retained tokens')
                require(place not in target_support or effect == 0, 'omitted transition changes target support')
    budget.tick()
    return dict(places=[problem['places'][p] for p in places], initial=[problem['initial'][p] for p in places],
                transitions=reduced_transitions, target=target)


def project(problem, places, transitions, deadline=None, max_work=DEFAULT_MAX_WORK):
    if deadline is None:
        deadline = time.monotonic() + 60
    return _project(problem, places, transitions, Budget(deadline, max_work))


def verify(problem, proof, check_inner, deadline=None, max_work=DEFAULT_MAX_WORK):
    if deadline is None:
        deadline = time.monotonic() + 60
    budget = Budget(deadline, max_work)
    budget.tick()
    require(type(proof) is dict and set(proof) == {'kind', 'places', 'transitions', 'inner'},
            'invalid relevance proof fields')
    require(proof['kind'] == 'relevance-v1', 'invalid relevance proof kind')
    require(type(proof['inner']) is dict, 'invalid relevance inner proof')
    reduced = _project(problem, proof['places'], proof['transitions'], budget)
    result = check_inner(reduced, proof['inner'])
    budget.tick()
    require(type(result) is str and result.startswith('python-'), 'inner proof has no independent verification')
    return 'python-relevance'
