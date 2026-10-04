import itertools
import random
import time
import unittest

from dag_checker import Budget, Encoding, Rup, encode, verify, verify_rup


def budget(work=1_000_000):
    return Budget(time.monotonic() + 10, work)


class RupTests(unittest.TestCase):
    def test_unsatisfiable_with_nontrivial_additions(self):
        e = Encoding(2, [[1, 2], [1, -2], [-1, 2], [-1, -2]], [])
        self.assertEqual(verify_rup(e, [[1], []], budget()), "python-dag-cnf-rup")

    def test_rejects_invalid_proof(self):
        e = Encoding(2, [[1, 2]], [])
        for additions in ([], [[1]], [[]], [[-1], []], [[True], []], [[3], []], [[0], []], [[1.0], []]):
            with self.subTest(additions=additions), self.assertRaises(ValueError):
                verify_rup(e, additions, budget())

    def test_watch_mutation_preserves_soundness(self):
        rng = random.Random(197)
        for _ in range(30):
            clauses = [[rng.choice([-1, 1]) * rng.randrange(1, 5) for _ in range(rng.randrange(1, 5))] for _ in range(8)]
            checker = Rup(4, clauses, budget())
            models = [values for values in itertools.product([False, True], repeat=4)
                      if all(any(values[abs(lit)-1] == (lit > 0) for lit in c) for c in clauses)]
            for _ in range(30):
                c = [rng.choice([-1, 1]) * rng.randrange(1, 5) for _ in range(rng.randrange(0, 5))]
                if checker.implied(c):
                    self.assertTrue(all(any(values[abs(lit)-1] == (lit > 0) for lit in c) for values in models))
                    checker.add(c)

    def test_limits_do_not_accept_partial_proofs(self):
        e = Encoding(1, [[1], [-1]], [])
        with self.assertRaises(TimeoutError):
            verify_rup(e, [[]], budget(0))
        with self.assertRaises(TimeoutError):
            verify_rup(e, [[]], Budget(time.monotonic() - 1, 100))




def problem(initial, transitions, target):
    return dict(places=[str(i) for i in range(len(initial))], initial=initial,
                transitions=[dict(name=str(i), pre=pre, post=post) for i, (pre, post) in enumerate(transitions)],
                target=target)


def constraint(coefficients, bound, equality=False):
    return dict(coefficients=coefficients, bound=bound, equality=equality)


class EncodingTests(unittest.TestCase):
    def compare_all_choices(self, p, controls):
        e = encode(p, controls)
        checker = Rup(e.variables, e.clauses, budget(10_000_000))
        for bits in itertools.product([False, True], repeat=len(e.choices)):
            assumptions = [lit if yes else -lit for (_, lit), yes in zip(e.choices, bits)]
            cnf_accepts = not checker.implied([-lit for lit in assumptions])
            marking = p['initial'][:]
            valid = True
            for (tid, _), yes in zip(e.choices, bits):
                if not yes:
                    continue
                tr = p['transitions'][tid]
                if any(marking[i] < w for i, w in tr['pre']):
                    valid = False
                    break
                for i, w in tr['pre']: marking[i] -= w
                for i, w in tr['post']: marking[i] += w
            for c in p['target']:
                value = sum(a*x for a, x in zip(c['coefficients'], marking))
                valid &= value == c['bound'] if c['equality'] else value >= c['bound']
            self.assertEqual(cnf_accepts, valid, (bits, marking, p))

    def test_weighted_counters_signed_targets_and_arbitrary_stop(self):
        transitions = [([[0, 1], [3, 2]], [[1, 1], [4, 3]]),
                       ([[0, 1]], [[2, 1], [3, 2]]),
                       ([[1, 1], [4, 1]], [[2, 1], [3, 4]])]
        for equality in (False, True):
            for bound in (-5, 0, 3, 7, 15):
                p = problem([1, 0, 0, 2, 0], transitions, [constraint([0, 0, 0, 2, -3], bound, equality)])
                self.compare_all_choices(p, [0, 1, 2])

    def test_random_dags_against_original_execution(self):
        rng = random.Random(290)
        for _ in range(30):
            transitions = []
            for source, target in ((0, 1), (0, 2), (1, 2)):
                pre = [[source, 1]]
                post = [[target, 1]]
                for p in (3, 4):
                    a, b = rng.randrange(4), rng.randrange(4)
                    if a: pre.append([p, a])
                    if b: post.append([p, b])
                transitions.append((pre, post))
            p = problem([1, 0, 0, rng.randrange(4), rng.randrange(4)], transitions,
                        [constraint([rng.randrange(-3, 4) for _ in range(5)], rng.randrange(-8, 9), bool(rng.randrange(2)))])
            self.compare_all_choices(p, [0, 1, 2])

    def test_guard_larger_than_width_and_exact_large_arithmetic(self):
        p = problem([1, 0, 0], [([[0, 1], [2, 100]], [[1, 1], [2, 99]])], [constraint([0, 1, 0], 1)])
        self.compare_all_choices(p, [0, 1])
        p = problem([1, 0, 2**64-1], [([[0, 1]], [[1, 1], [2, 2**64-1]])],
                    [constraint([0, 0, -2**63], -2**63)])
        self.compare_all_choices(p, [0, 1])

    def test_rejects_cycles_stutters_bad_conservation_and_schema(self):
        for transitions in ([([[0, 1]], [[0, 1]])],
                            [([], [[2, 1]])],
                            [([[0, 1]], [[1, 2]])],
                            [([[0, 1]], [[1, 1]]), ([[1, 1]], [[0, 1]])]):
            p = problem([1, 0, 0], transitions, [])
            with self.assertRaises(ValueError): encode(p, [0, 1])
        p = problem([1, 0], [], [])
        for controls in ([], [1, 0], [0, 0], [True], [2]):
            with self.assertRaises(ValueError): encode(p, controls)
        p['initial'][0] = True
        with self.assertRaises(ValueError): encode(p, [0])

    def test_impossible_multitoken_transition_is_ignored(self):
        p = problem([1, 0], [([[0, 2]], [[1, 2]])], [constraint([0, 1], 1)])
        e = encode(p, [0, 1])
        self.assertEqual(e.choices, [])
        proof = dict(kind='dag-cnf-rup-v1', control_places=[0, 1], additions=[[]])
        self.assertEqual(verify(p, proof), 'python-dag-cnf-rup')
        p['target'] = []
        with self.assertRaises(ValueError): verify(p, proof)

    def test_certificate_schema_original_mutation_and_limits(self):
        p = problem([1, 0], [], [constraint([0, 1], 1)])
        proof = dict(kind='dag-cnf-rup-v1', control_places=[0, 1], additions=[[]])
        verify(p, proof)
        for changed in (dict(proof, trusted=True), dict(proof, kind='other'), dict(proof, additions=[])):
            with self.assertRaises(ValueError): verify(p, changed)
        with self.assertRaises(TimeoutError): verify(p, proof, max_work=0)
        with self.assertRaises(TimeoutError): verify(p, proof, deadline=time.monotonic()-1)
        p['initial'] = [0, 1]
        with self.assertRaises(ValueError): verify(p, proof)

    def test_unreachable_cycle_is_ignored(self):
        p = problem([1, 0], [([[1, 1]], [[1, 1]])], [])
        self.compare_all_choices(p, [0, 1])


if __name__ == '__main__':
    unittest.main()
