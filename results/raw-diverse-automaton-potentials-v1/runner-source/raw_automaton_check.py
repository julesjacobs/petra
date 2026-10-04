"""Exact fixed-Parikh membership via connected integral flow on a serial NFA.

Integral edge counts with Euler balances and rooted connected support admit an
Euler trail. Its labels have exactly the requested response multiplicities.
This is independent of the Rust residual-vector search.
"""
import math
import time


def member(automaton, responses, marking, deadline, z3_module=None):
    if z3_module is None:
        import z3 as z3_module
    z3 = z3_module
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError('serial automaton checking deadline')
    solver = z3.Solver()
    counts = [z3.Int(f'edge_{i}') for i in range(len(automaton['edges']))]
    ranks = [z3.Int(f'rank_{i}') for i in range(automaton['states'])]
    ends = [z3.Bool(f'end_{i}') for i in range(automaton['states'])]
    incoming = [[] for _ in ranks]
    outgoing = [[] for _ in ranks]
    labels = {p: [] for p in responses}
    total = lambda xs: z3.Sum(xs) if xs else z3.IntVal(0)
    for i, edge in enumerate(automaton['edges']):
        if time.monotonic() >= deadline:
            raise TimeoutError('serial automaton formula deadline')
        outgoing[edge['source']].append(i)
        incoming[edge['target']].append(i)
        labels[edge['response']].append(i)
        solver.add(counts[i] >= 0)
    accepting = set(automaton['accepting'])
    solver.add(total([z3.If(end, 1, 0) for end in ends]) == 1)
    for state in range(automaton['states']):
        if time.monotonic() >= deadline:
            raise TimeoutError('serial automaton formula deadline')
        ins = total([counts[i] for i in incoming[state]])
        outs = total([counts[i] for i in outgoing[state]])
        solver.add(ins + int(state == automaton['initial']) == outs + z3.If(ends[state], 1, 0))
        solver.add(ranks[state] >= 0, ranks[state] < automaton['states'])
        if state not in accepting:
            solver.add(z3.Not(ends[state]))
        if state == automaton['initial']:
            solver.add(ranks[state] == 0)
        else:
            predecessors = [z3.And(counts[i] > 0,
                                  ranks[automaton['edges'][i]['source']] < ranks[state])
                            for i in incoming[state]]
            solver.add(z3.Implies(ins + outs > 0, z3.Or(predecessors)))
    for place, indices in labels.items():
        solver.add(total([counts[i] for i in indices]) == marking[place])
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError('serial automaton formula deadline')
    solver.set(timeout=max(1, math.ceil(remaining * 1000)))
    result = solver.check()
    if result == z3.unknown or time.monotonic() >= deadline:
        raise TimeoutError('serial automaton membership inconclusive')
    return result == z3.sat
