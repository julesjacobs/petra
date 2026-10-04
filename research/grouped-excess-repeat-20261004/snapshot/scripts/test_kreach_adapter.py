#!/usr/bin/env python3
import ast
import random
import unittest
from kreach_adapter import reduce_problem, split_transitions, kvass


def reachable(problem):
    seen = {tuple(problem['initial'])}
    pending = list(seen)
    while pending:
        marking = pending.pop()
        values = [sum(a*x for a,x in zip(c['coefficients'], marking)) for c in problem['target']]
        if all(v == c['bound'] if c['equality'] else v >= c['bound'] for v,c in zip(values,problem['target'])):
            return True
        for t in problem['transitions']:
            if any(marking[p] < w for p,w in t['pre']):
                continue
            nxt = list(marking)
            for p,w in t['pre']: nxt[p] -= w
            for p,w in t['post']: nxt[p] += w
            nxt = tuple(nxt)
            if nxt not in seen:
                seen.add(nxt)
                pending.append(nxt)
        if len(seen) > 100_000:
            raise AssertionError('test fixture unexpectedly large')
    return False


def as_petri_net(text):
    start,initial,finish,target,edges = ast.literal_eval(text)
    n = len(initial)
    states = max([start,finish]+[x for source,dest,effect in edges for x in [source,dest]])+1
    initial = initial+[int(i==start) for i in range(states)]
    goal = target+[int(i==finish) for i in range(states)]
    transitions = []
    for source,dest,effect in edges:
        transitions.append(dict(pre=[(n+source,1)]+[(i,-x) for i,x in enumerate(effect) if x<0],
            post=[(n+dest,1)]+[(i,x) for i,x in enumerate(effect) if x>0]))
    return dict(initial=initial,transitions=transitions,target=[dict(coefficients=[int(i==j) for i in range(len(initial))],bound=x,equality=True) for j,x in enumerate(goal)])


class AdapterTests(unittest.TestCase):
    def test_signed_conjunctions_against_finite_closure(self):
        rng = random.Random(704)
        for case in range(150):
            problem = dict(places=['x','y'], initial=[2,0],
                transitions=[dict(pre=[(rng.randrange(2),1)],post=[(rng.randrange(2),1)]) for _ in range(3)],
                target=[dict(coefficients=[rng.randrange(-2,3),rng.randrange(-2,3)],bound=rng.randrange(-3,4),equality=bool(rng.randrange(2))) for _ in range(2)])
            self.assertEqual(reachable(problem), reachable(split_transitions(reduce_problem(problem))), case)
            self.assertEqual(reachable(problem), reachable(as_petri_net(kvass(problem))), case)


if __name__ == '__main__':
    unittest.main()
