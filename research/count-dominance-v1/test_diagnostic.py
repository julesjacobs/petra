import itertools
import random
import unittest

from diagnostic import Limits, independently_check, replay


def problem(initial, arcs, target):
    return dict(places=[f"p{i}" for i in range(len(initial))], initial=initial,
                transitions=[dict(name=f"t{i}", pre=pre, post=post)
                             for i, (pre, post) in enumerate(arcs)], target=target)


def constraint(coefficients, bound, equality=False):
    return dict(coefficients=coefficients, bound=bound, equality=equality)


def reference_words(p, bounds, depth=None):
    pending = [(tuple(p["initial"]), (0,) * len(bounds), ())]
    states = {}
    witnesses = []
    frontier = set()
    while pending:
        marking, used, word = pending.pop()
        states[used] = marking
        target = True
        for c in p["target"]:
            lhs = sum(marking[q] * a for q, a in enumerate(c["coefficients"]))
            target = target and (lhs == c["bound"] if c["equality"] else lhs >= c["bound"])
        if target:
            witnesses.append((used, word))
        if depth is not None and len(word) >= depth:
            continue
        for t, transition in enumerate(p["transitions"]):
            next_marking = list(marking)
            possible = True
            for q, n in transition["pre"]:
                if marking[q] < n:
                    possible = False
                    break
                next_marking[q] -= n
            if not possible:
                continue
            if used[t] == bounds[t]:
                frontier.add((t, bounds[t]))
                continue
            for q, n in transition["post"]:
                next_marking[q] += n
            next_used = list(used)
            next_used[t] += 1
            pending.append((tuple(next_marking), tuple(next_used), word + (t,)))
    return states, witnesses, frontier


class DominanceTests(unittest.TestCase):
    def test_self_loop_eliminates_spurious_frontier(self):
        p = problem([1, 0, 0, 0], [
            ([(0, 1)], [(1, 1), (2, 2)]),
            ([(1, 1), (2, 3)], [(0, 1), (3, 1)]),
            ([(0, 1)], [(0, 1)]),
        ], [constraint([1, 0, 0, 0], 0, True),
            constraint([0, 1, 0, 0], 1, True),
            constraint([0, 0, 1, 0], 1, True),
            constraint([0, 0, 0, 1], 1, True)])
        baseline = replay(p, [2, 1, 50])
        candidate = replay(p, [2, 1, 50], True)
        self.assertEqual(baseline[0]["nodes"], 102)
        self.assertEqual(baseline[0]["frontier"], [[2, 50]])
        self.assertEqual(candidate[0]["nodes"], 2)
        self.assertEqual(candidate[0]["frontier"], [])
        self.assertEqual(candidate[0]["dominated_prefixes"], 1)
        self.assertEqual(independently_check(p, [2, 1, 50], baseline, candidate)["status"], "passed")

    def test_incomparable_budgets_are_retained(self):
        p = problem([0], [([], [(0, 1)]), ([], [(0, 1)])],
                    [constraint([1], 3)])
        baseline = replay(p, [1, 1])
        candidate = replay(p, [1, 1], True)
        self.assertEqual(candidate[0]["status"], "complete")
        self.assertEqual(candidate[0]["nodes"], 4)
        self.assertEqual(candidate[0]["peak_vectors_per_marking"], 2)
        budgets = {candidate[1][i].remaining for i in candidate[2][(1,)]}
        self.assertEqual(budgets, {(1, 0), (0, 1)})
        self.assertEqual(independently_check(p, [1, 1], baseline, candidate)["status"], "passed")

    def test_initial_and_prefix_witnesses_are_replayed(self):
        for target in [0, 2]:
            p = problem([0], [([], [(0, 1)]), ([], [])],
                        [constraint([1], target, True)])
            candidate = replay(p, [5, 5], True)
            self.assertEqual(candidate[0]["status"], "witness")
            self.assertEqual(len(candidate[0]["witness"]), target)
            self.assertEqual(independently_check(p, [5, 5], candidate, candidate)["status"], "passed")

    def test_all_resource_limits_preserve_incompleteness(self):
        p = problem([0], [([], [(0, 1)])], [constraint([1], 9)])
        for limits, reason in [(Limits(states=1), "states"), (Limits(work=0), "work"),
                               (Limits(seconds=0), "wall"), (Limits(cells=1), "cells")]:
            for dominance in [False, True]:
                out = replay(p, [5], dominance, limits)[0]
                self.assertEqual(out["status"], "incomplete")
                self.assertEqual(out["limit"], reason)
                self.assertIsNone(out["frontier"])

    def test_differential_small_nets_and_global_frontier_condition(self):
        rng = random.Random(20261003)
        completed = 0
        witnesses = 0
        for _ in range(120):
            arcs = []
            for _ in range(2):
                pre = [(q, n) for q in range(2) if (n := rng.randrange(3))]
                post = [(q, n) for q in range(2) if (n := rng.randrange(3))]
                arcs.append((pre, post))
            p = problem([rng.randrange(3), rng.randrange(3)], arcs,
                        [constraint([rng.randrange(-1, 2), rng.randrange(-1, 2)],
                                    rng.randrange(-2, 4), bool(rng.randrange(2)))])
            for bounds in itertools.product(range(3), repeat=2):
                states, accepted, exact_frontier = reference_words(p, bounds)
                baseline = replay(p, bounds)
                candidate = replay(p, bounds, True)
                self.assertNotEqual(candidate[0]["status"], "incomplete")
                self.assertEqual(candidate[0]["status"] == "witness", bool(accepted))
                self.assertEqual(baseline[0]["status"] == "witness", bool(accepted))
                if accepted:
                    witnesses += 1
                else:
                    completed += 1
                    self.assertEqual(baseline[0]["nodes"], len(states))
                    self.assertEqual(set(map(tuple, baseline[0]["frontier"])), exact_frontier)
                    _, broader_witnesses, _ = reference_words(p, [6, 6], depth=6)
                    for used, _ in broader_witnesses:
                        self.assertTrue(any(used[t] > n for t, n in candidate[0]["frontier"]))
                self.assertEqual(independently_check(p, bounds, baseline, candidate)["status"], "passed")
        self.assertGreater(completed, 100)
        self.assertGreater(witnesses, 100)

    def test_checker_rejects_deleted_incomparable_representative(self):
        p = problem([0], [([], [(0, 1)]), ([], [(0, 1)])], [constraint([1], 3)])
        baseline = replay(p, [1, 1])
        candidate = replay(p, [1, 1], True)
        candidate[2][(1,)].pop()
        with self.assertRaises(AssertionError):
            independently_check(p, [1, 1], baseline, candidate)


if __name__ == "__main__":
    unittest.main()
