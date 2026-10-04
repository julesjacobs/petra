import copy
import itertools
import time
import unittest

from grouped_excess_checker import verify


def problem():
    return dict(places=['a', 'b', 'reserve'], initial=[2, 1, 0], transitions=[
        dict(name='transfer', pre=[[0, 2], [1, 1]], post=[[1, 2]]),
        dict(name='return', pre=[[0, 1]], post=[[2, 1]]),
        dict(name='restore', pre=[[2, 1]], post=[[0, 1]])],
        target=[dict(coefficients=[1, 0, 0], bound=3, equality=False)])


def proof():
    return dict(kind='grouped-excess-v1', groups=[[0, 2], [1]], thresholds=[1, 1],
                target_row=0, sign=1)


class GroupedExcessTests(unittest.TestCase):
    def test_nonlinear_invariant_and_integration(self):
        p, c = problem(), proof()
        self.assertEqual(verify(p, c), 'python-grouped-excess')
        from benchmark import verify as verify_answer
        self.assertEqual(verify_answer(p, dict(verdict='unreachable', proof=c)),
                         'python-grouped-excess')

    def test_induction_requires_original_read_guards(self):
        p = problem()
        p['transitions'][0]['pre'][0][1] = 1
        with self.assertRaisesRegex(ValueError, 'increase'):
            verify(p, proof())
        p = problem()
        p['transitions'][0] = dict(name='read', pre=[[0, 2]], post=[[0, 2], [1, 1]])
        with self.assertRaisesRegex(ValueError, 'increase'):
            verify(p, proof())

    def test_target_sign_and_large_exact_arithmetic(self):
        p, c = problem(), proof()
        p['target'] = [dict(coefficients=[-2**63, 0, 0], bound=-2**63, equality=True)]
        c['sign'] = -1
        with self.assertRaisesRegex(ValueError, 'exclude'):
            verify(p, c)
        p['initial'] = [0, 0, 0]
        c['thresholds'] = [0, 0]
        self.assertEqual(verify(p, c), 'python-grouped-excess')
        p['target'][0]['equality'] = False
        with self.assertRaisesRegex(ValueError, 'inequality'):
            verify(p, c)

    def test_malformed_proofs_and_resource_limits(self):
        for patch in [dict(groups=[[0], [1]]), dict(groups=[[0, 2], [1, 2]]),
                      dict(groups=[[2, 0], [1]]), dict(thresholds=[-1, 1]),
                      dict(thresholds=[True, 1]), dict(sign=True), dict(target_row=1),
                      dict(untrusted=True), dict(groups=[[0, 2], []])]:
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                verify(problem(), dict(proof(), **patch))
        for options in [dict(max_work=0), dict(deadline=time.monotonic())]:
            with self.assertRaises(TimeoutError):
                verify(problem(), proof(), **options)
        p = problem()
        p['transitions'][0]['pre'].append([0, 1])
        with self.assertRaises(ValueError):
            verify(p, proof())

    def test_every_accepted_weighted_proof_matches_exhaustive_reachability(self):
        accepted = 0
        for initial in itertools.product(range(3), repeat=2):
            for pre in itertools.product(range(3), repeat=2):
                for post in itertools.product(range(3), repeat=2):
                    if sum(post) > sum(pre):
                        continue
                    p = dict(places=['a', 'b'], initial=list(initial), transitions=[
                        dict(name='t', pre=[[i, n] for i, n in enumerate(pre) if n],
                             post=[[i, n] for i, n in enumerate(post) if n])],
                        target=[dict(coefficients=[1, -1], bound=3, equality=False)])
                    seen = {initial}
                    pending = [initial]
                    while pending:
                        m = pending.pop()
                        if all(a >= b for a, b in zip(m, pre)):
                            successor = tuple(a-b+c for a, b, c in zip(m, pre, post))
                            if successor not in seen:
                                seen.add(successor)
                                pending.append(successor)
                    for equality, sign in [(False, 1), (True, 1), (True, -1)]:
                        p['target'][0].update(equality=equality, bound=3 if sign == 1 else -3)
                        c = dict(kind='grouped-excess-v1', groups=[[0], [1]],
                                 thresholds=[1, 1], target_row=0, sign=sign)
                        try:
                            verify(p, c)
                        except ValueError:
                            continue
                        accepted += 1
                        bound = p['target'][0]['bound']
                        self.assertTrue(all((m[0]-m[1] != bound) if equality
                                            else (m[0]-m[1] < bound) for m in seen))
        self.assertGreater(accepted, 100)


if __name__ == '__main__':
    unittest.main()
