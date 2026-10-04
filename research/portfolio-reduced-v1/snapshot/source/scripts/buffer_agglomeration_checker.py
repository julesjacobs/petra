"""Independently reconstruct uniform-weight eager/delayed buffer agglomeration.

Only an independently checked inner proof on the reconstructed net establishes
unreachability. Certificate steps use stable original place indices.
"""
import math
import time

DEFAULT_MAX_WORK = 20_000_000
MAX_STABLE_TRANSITIONS = 1_000_000
MAX_STABLE_ARCS = 20_000_000


def require(condition, message):
    if not condition:
        raise ValueError(message)


class Budget:
    def __init__(self, deadline, max_work):
        require(type(deadline) in (int, float) and math.isfinite(deadline), 'invalid deadline')
        require(type(max_work) is int and max_work >= 0, 'invalid work limit')
        self.deadline = deadline
        self.remaining = max_work

    def tick(self, work=1):
        self.remaining -= work
        if self.remaining < 0 or time.monotonic() >= self.deadline:
            raise TimeoutError('buffer agglomeration verification limit')


def fields(value, names):
    require(type(value) is dict and len(value) == len(names) and all(name in value for name in names),
            'invalid fields')


def integer(value, lower, upper):
    require(type(value) is int and lower <= value < upper, 'invalid integer')


def _reconstruct(problem, steps, budget):
    budget.tick()
    fields(problem, ('places', 'initial', 'transitions', 'target'))
    places, initial = problem['places'], problem['initial']
    require(type(places) is list and type(initial) is list and len(initial) == len(places),
            'invalid marking dimension')
    n = len(places)
    require(type(steps) is list and 0 < len(steps) <= n, 'invalid reduction steps')
    budget.tick(4*n + len(steps))
    visible, removed = [False]*n, [False]*n
    incoming, outgoing = [{} for _ in range(n)], [{} for _ in range(n)]
    for name, tokens in zip(places, initial):
        budget.tick()
        require(type(name) is str, 'invalid place name')
        budget.tick(len(name))
        integer(tokens, 0, 2**64)
    require(type(problem['target']) is list, 'invalid target')
    for row in problem['target']:
        budget.tick()
        fields(row, ('coefficients', 'bound', 'equality'))
        require(type(row['coefficients']) is list and len(row['coefficients']) == n,
                'target dimension mismatch')
        integer(row['bound'], -2**63, 2**63)
        require(type(row['equality']) is bool, 'invalid equality flag')
        for i, coefficient in enumerate(row['coefficients']):
            budget.tick()
            integer(coefficient, -2**63, 2**63)
            visible[i] |= coefficient != 0
    require(type(problem['transitions']) is list, 'invalid transitions')
    limit = min(MAX_STABLE_TRANSITIONS, max(1024, 4*len(problem['transitions'])))
    require(len(problem['transitions']) <= limit, 'stable transition limit')
    budget.tick(len(problem['transitions']))
    stable, active, stable_arcs = [], [], 0
    for transition in problem['transitions']:
        budget.tick()
        fields(transition, ('name', 'pre', 'post'))
        require(type(transition['name']) is str, 'invalid transition name')
        budget.tick(len(transition['name']))
        copied = dict(name=transition['name'])
        tid = len(stable)
        for side in ('pre', 'post'):
            arcs = transition[side]
            require(type(arcs) is list, 'invalid arcs')
            stable_arcs += len(arcs)
            require(stable_arcs <= MAX_STABLE_ARCS, 'stable arc limit')
            budget.tick(len(arcs))
            seen, checked = set(), []
            for arc in arcs:
                budget.tick()
                require(type(arc) is list and len(arc) == 2, 'invalid arc')
                place, weight = arc
                integer(place, 0, n)
                integer(weight, 1, 2**64)
                require(place not in seen, 'duplicate arc')
                seen.add(place)
                checked.append([place, weight])
                (outgoing if side == 'pre' else incoming)[place][tid] = weight
            copied[side] = checked
        stable.append(copied)
        active.append(True)

    def merge(arcs, other, place):
        merged = {}
        for side in (arcs, other):
            for i, weight in side:
                budget.tick()
                if i != place:
                    total = merged.get(i, 0) + weight
                    integer(total, 1, 2**64)
                    merged[i] = total
        budget.tick(len(merged)*max(1, len(merged).bit_length()))
        return [[i, merged[i]] for i in sorted(merged)]

    for step in steps:
        budget.tick()
        fields(step, ('place', 'orientation'))
        place, orientation = step['place'], step['orientation']
        integer(place, 0, n)
        require(type(orientation) is str and orientation in ('eager', 'delayed'), 'invalid orientation')
        require(not removed[place], 'place already removed')
        require(initial[place] == 0 and not visible[place], 'buffer is marked or queried')
        budget.tick(sum(len(ids)*max(1, len(ids).bit_length()) for ids in (incoming[place], outgoing[place])))
        producers, consumers = sorted(incoming[place]), sorted(outgoing[place])
        weight = None
        for incident in (incoming[place], outgoing[place]):
            for count in incident.values():
                budget.tick()
                require(weight is None or weight == count, 'nonuniform buffer weights')
                weight = count
        require(producers and consumers, 'buffer needs producers and consumers')
        budget.tick(len(producers)+len(consumers))
        require(set(producers).isdisjoint(consumers), 'buffer self-loop')
        if orientation == 'eager':
            for tid in consumers:
                transition = stable[tid]
                require(transition['pre'] == [[place, weight]], 'consumer has other inputs')
                for i, _ in transition['post']:
                    budget.tick()
                    require(not visible[i], 'consumer output is queried')
        else:
            for tid in producers:
                transition = stable[tid]
                require(transition['post'] == [[place, weight]], 'producer has other outputs')
                for i, _ in transition['pre']:
                    budget.tick()
                    require(not visible[i], 'producer input is queried')
        added = len(producers)*len(consumers)
        require(len(stable)+added <= limit, 'stable transition limit')
        budget.tick(added)
        macros = []
        for producer in producers:
            for consumer in consumers:
                budget.tick()
                first, second = stable[producer], stable[consumer]
                if orientation == 'eager':
                    budget.tick(len(first['pre']))
                    pre = [arc[:] for arc in first['pre']]
                    post = merge(first['post'], second['post'], place)
                else:
                    pre = merge(first['pre'], second['pre'], place)
                    budget.tick(len(second['post']))
                    post = [arc[:] for arc in second['post']]
                stable_arcs += len(pre)+len(post)
                require(stable_arcs <= MAX_STABLE_ARCS, 'stable arc limit')
                tid = len(stable)+len(macros)
                macros.append(dict(name=f'buffer-macro-{tid}', pre=pre, post=post))
        for tid in producers + consumers:
            budget.tick()
            active[tid] = False
            for side, index in (('pre', outgoing), ('post', incoming)):
                for i, _ in stable[tid][side]:
                    budget.tick()
                    del index[i][tid]
        for tid, transition in enumerate(macros, start=len(stable)):
            for side, index in (('pre', outgoing), ('post', incoming)):
                for i, count in transition[side]:
                    budget.tick()
                    index[i][tid] = count
        stable.extend(macros)
        active.extend([True]*len(macros))
        removed[place] = True
    budget.tick(n)
    kept = []
    mapping = {}
    for i in range(n):
        budget.tick()
        if not removed[i]:
            mapping[i] = len(kept)
            kept.append(i)
    projected = dict(places=[places[i] for i in kept], initial=[initial[i] for i in kept],
                     transitions=[], target=[])
    for tid, transition in enumerate(stable):
        budget.tick()
        if not active[tid]:
            continue
        result = dict(name=transition['name'], pre=[], post=[])
        for side in ('pre', 'post'):
            for i, count in transition[side]:
                budget.tick()
                require(i in mapping, 'active arc refers to removed place')
                result[side].append([mapping[i], count])
        projected['transitions'].append(result)
    for row in problem['target']:
        budget.tick(len(kept)+1)
        projected['target'].append(dict(coefficients=[row['coefficients'][i] for i in kept],
                                        bound=row['bound'], equality=row['equality']))
    budget.tick()
    return projected


def reconstruct(problem, steps, deadline=None, max_work=DEFAULT_MAX_WORK):
    deadline = time.monotonic()+60 if deadline is None else deadline
    return _reconstruct(problem, steps, Budget(deadline, max_work))


def verify(problem, proof, check_inner=None, deadline=None, max_work=DEFAULT_MAX_WORK):
    deadline = time.monotonic()+60 if deadline is None else deadline
    budget = Budget(deadline, max_work)
    budget.tick()
    fields(proof, ('kind', 'steps', 'inner'))
    require(type(proof['kind']) is str and proof['kind'] == 'buffer-agglomeration-v1', 'invalid proof kind')
    require(type(proof['inner']) is dict and callable(check_inner), 'invalid inner proof')
    reduced = _reconstruct(problem, proof['steps'], budget)
    checked = check_inner(reduced, proof['inner'])
    budget.tick()
    require(type(checked) is str and checked.startswith('python-'), 'inner proof has no independent verification')
    return 'python-buffer-agglomeration'
