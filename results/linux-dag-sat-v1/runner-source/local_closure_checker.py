"""Check a local necessary-target closure using the original weighted net.

For a >= constraint, omitted nonpositive coefficients contribute at most zero.
Dropping those terms is therefore a necessary condition on the projected marking.
Projected transitions overapproximate original enabling; a closed abstract state
set that excludes this necessary target proves original unreachability.
"""

I64_MIN = -(2**63)
I64_MAX = 2**63 - 1


def project(problem, places):
    assert isinstance(places, list)
    assert all(type(place) is int and 0 <= place < len(problem['places']) for place in places)
    assert places == sorted(set(places))
    ids = {place: index for index, place in enumerate(places)}
    target = []
    for constraint in problem['target']:
        coefficients = constraint['coefficients']
        bound = constraint['bound']
        assert len(coefficients) == len(problem['places'])
        assert all(type(a) is int and I64_MIN <= a <= I64_MAX for a in coefficients)
        assert type(bound) is int and I64_MIN <= bound <= I64_MAX
        assert type(constraint['equality']) is bool
        directions = [(coefficients, bound)]
        if constraint['equality'] and bound != I64_MIN and all(a != I64_MIN for a in coefficients):
            directions.append(([-a for a in coefficients], -bound))
        for terms, rhs in directions:
            if all(a <= 0 for place, a in enumerate(terms) if place not in ids):
                target.append(dict(coefficients=[terms[place] for place in places],
                                   bound=rhs, equality=False))
    transitions, seen = [], set()
    for transition in problem['transitions']:
        pre, post = [tuple(sorted((ids[place], weight) for place, weight in transition[side]
                                 if place in ids)) for side in ('pre', 'post')]
        if pre == post or (pre, post) in seen:
            continue
        seen.add((pre, post))
        transitions.append(dict(name=f'local-{len(transitions)}', pre=pre, post=post))
    return dict(places=[problem['places'][place] for place in places],
                initial=[problem['initial'][place] for place in places],
                transitions=transitions, target=target)


def verify_local_closure(problem, proof):
    from benchmark import verify_threshold_closure

    assert set(proof) == {'kind', 'places', 'closure'}
    assert proof['kind'] == 'local-closure-v1'
    closure = proof['closure']
    assert set(closure) == {'kind', 'thresholds', 'states'}
    assert closure['kind'] == 'threshold-closure-v1'
    projected = project(problem, proof['places'])
    verify_threshold_closure(projected, closure)
    return 'python-local-closure'
