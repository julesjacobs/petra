"""Independent checking of serial path schemas plus component invariants."""
import math
import time
from collections import Counter


def verify(q, proof, deadline, max_obligations=1_000_000):
    from raw_stress_worker import validate, U64_MAX
    from raw_invariant_check import verify as check_components

    def require(condition, message):
        if not condition:
            raise ValueError(message)

    require(type(deadline) in (int, float) and math.isfinite(deadline), 'invalid deadline')
    require(type(max_obligations) is int and max_obligations >= 0, 'invalid work limit')
    remaining = max_obligations

    def tick(amount=1):
        nonlocal remaining
        remaining -= amount
        if remaining < 0 or time.monotonic() >= deadline:
            raise TimeoutError('serial schema checking limit')

    def fields(value, names):
        tick()
        require(type(value) is dict and set(value) == set(names.split()), 'invalid serial schema fields')

    tick()
    require(type(q) is dict and type(q.get('target')) is dict, 'invalid original raw query')
    for field in ('places', 'initial', 'transitions'):
        require(type(q.get(field)) is list, 'invalid original raw query field')
        tick(len(q[field]))
    for field in ('zero_places', 'response_places'):
        require(type(q['target'].get(field)) is list, 'invalid target places')
        tick(len(q['target'][field]))
    for transition in q['transitions']:
        tick()
        require(type(transition) is dict, 'invalid transition')
        for field in ('pre', 'post'):
            require(type(transition.get(field)) is list, 'invalid transition arcs')
            tick(len(transition[field]))
    a = q['target'].get('excluded_automaton')
    require(type(a) is dict, 'serial schemas require an automaton target')
    for field in ('edges', 'accepting'):
        require(type(a.get(field)) is list, 'invalid automaton fields')
        tick(len(a[field]))
    validate(q)
    require(q['format'] == 'ser-raw-v2', 'serial schemas require an automaton target')
    fields(proof, 'format schemas invariant')
    require(proof['format'] == 'raw-automaton-invariant-v1', 'invalid schema proof format')
    require(type(proof['schemas']) is list, 'invalid schemas')
    automaton = q['target']['excluded_automaton']

    def walk(state, path, counts):
        require(type(path) is list, 'invalid serial path')
        for index in path:
            tick()
            require(type(index) is int and 0 <= index < len(automaton['edges']), 'invalid serial edge index')
            edge = automaton['edges'][index]
            require(edge['source'] == state, 'disconnected serial path')
            counts[edge['response']] += 1
            require(counts[edge['response']] <= U64_MAX, 'serial vector overflow')
            state = edge['target']
        return state

    components = []
    for schema in proof['schemas']:
        fields(schema, 'segments')
        require(type(schema['segments']) is list, 'invalid serial segments')
        state, base, periods = automaton['initial'], Counter(), []
        for segment in schema['segments']:
            fields(segment, 'path cycles')
            state = walk(state, segment['path'], base)
            require(type(segment['cycles']) is list, 'invalid serial cycles')
            for cycle in segment['cycles']:
                tick()
                require(type(cycle) is list and len(cycle) > 0, 'empty or invalid serial cycle')
                period = Counter()
                require(walk(state, cycle, period) == state, 'serial cycle does not close')
                periods.append([[p, count] for p, count in sorted(period.items())])
        tick(len(automaton['accepting']))
        require(state in automaton['accepting'], 'nonaccepting serial schema endpoint')
        components.append(dict(base=[[p, count] for p, count in sorted(base.items())], periods=periods))
    tick(len(q['places']) + len(q['transitions']))
    for transition in q['transitions']:
        tick(len(transition['pre']) + len(transition['post']))
    target = dict(q['target'], kind='completed-outside-semilinear', excluded_semilinear=components)
    del target['excluded_automaton']
    subset = dict(q, format='ser-raw-v1', target=target)
    require(check_components(subset, proof['invariant'], deadline, remaining) == 'python-raw-component-invariant',
            'unchecked component invariant')
    tick()
    return 'python-raw-automaton-invariant'
