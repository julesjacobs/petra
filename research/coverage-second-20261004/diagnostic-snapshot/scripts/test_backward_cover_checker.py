import itertools
import time
import unittest

from backward_cover_checker import verify


def example():
    return dict(places=['a', 'b', 'guard'], initial=[0, 0, 1], transitions=[
        dict(name='move', pre=[[0, 1], [2, 1]], post=[[1, 1], [2, 1]])],
        target=[dict(coefficients=[0, 1, 0], bound=1, equality=False)])


def certificate():
    return dict(kind='backward-cover-v1', requirements=[
        dict(target_row=0, sign=1, place=1, required=1)],
        basis=[[[1, 1]], [[0, 1], [2, 1]]])


class BackwardCoverTests(unittest.TestCase):
    def test_guarded_predecessor_and_integration(self):
        self.assertEqual(verify(example(), certificate()), 'python-backward-cover')
        from benchmark import verify as verify_answer
        self.assertEqual(verify_answer(example(), dict(verdict='unreachable', proof=certificate())),
                         'python-backward-cover')

    def test_omitted_guard_cannot_establish_negative_claim(self):
        p, c = example(), certificate()
        p['initial'] = [1, 0, 1]
        with self.assertRaisesRegex(ValueError, 'initial'):
            verify(p, c)
        p['initial'] = [1, 0, 0]
        self.assertEqual(verify(p, c), 'python-backward-cover')
        p['transitions'][0]['pre'] = [[0, 1]]
        with self.assertRaisesRegex(ValueError, 'closed'):
            verify(p, c)

    def test_conjunctive_goal_and_token_bound(self):
        p = dict(places=['a', 'b'], initial=[1, 0], transitions=[
            dict(name='forward', pre=[[0, 1]], post=[[1, 1]]),
            dict(name='back', pre=[[1, 1]], post=[[0, 1]])], target=[
            dict(coefficients=[1, 0], bound=1, equality=False),
            dict(coefficients=[0, 1], bound=1, equality=False)])
        c = dict(kind='backward-cover-v1', requirements=[
            dict(target_row=0, sign=1, place=0, required=1),
            dict(target_row=1, sign=1, place=1, required=1)], basis=[])
        self.assertEqual(verify(p, c), 'python-backward-cover')
        p['transitions'].append(dict(name='grow', pre=[[0, 1]], post=[[0, 1], [1, 1]]))
        with self.assertRaisesRegex(ValueError, 'goal'):
            verify(p, c)

    def test_signed_requirement_rounding_and_exact_large_arithmetic(self):
        p = dict(places=['a'], initial=[0], transitions=[],
                 target=[dict(coefficients=[-2**63], bound=-2**63, equality=True)])
        c = dict(kind='backward-cover-v1', requirements=[
            dict(target_row=0, sign=-1, place=0, required=1)], basis=[])
        self.assertEqual(verify(p, c), 'python-backward-cover')
        p['target'][0] = dict(coefficients=[2], bound=3, equality=False)
        c['requirements'][0].update(sign=1, required=2)
        self.assertEqual(verify(p, c), 'python-backward-cover')
        c['requirements'][0]['required'] = 1
        with self.assertRaisesRegex(ValueError, 'incorrect'):
            verify(p, c)

    def test_closure_without_token_bound_and_overflow(self):
        p = dict(places=['a', 'b'], initial=[0, 0], transitions=[
            dict(name='grow-a', pre=[[0, 2**64-1]], post=[[0, 2**64-1], [1, 1]])],
            target=[dict(coefficients=[0, 1], bound=1, equality=False)])
        c = dict(kind='backward-cover-v1', requirements=[
            dict(target_row=0, sign=1, place=1, required=1)],
            basis=[[[1, 1]], [[0, 2**64-1]]])
        self.assertEqual(verify(p, c), 'python-backward-cover')
        c['basis'] = [[[1, 1]]]
        with self.assertRaisesRegex(ValueError, 'closed'):
            verify(p, c)

    def test_predecessor_arithmetic_exceeds_u64_exactly(self):
        p = dict(places=['a', 'b', 'grow'], initial=[0, 0, 0], transitions=[
            dict(name='move', pre=[[0, 2**64-1]], post=[[1, 1]]),
            dict(name='disable-bound', pre=[], post=[[2, 1]])],
            target=[dict(coefficients=[0, 1, 0], bound=1, equality=False)])
        c = dict(kind='backward-cover-v1', requirements=[
            dict(target_row=0, sign=1, place=1, required=1)],
            basis=[[[1, 1]], [[0, 2**64-1]], [[0, 2**64-1], [1, 1]]])
        self.assertEqual(verify(p, c), 'python-backward-cover')

    def test_strict_schema_and_limits(self):
        for patch in [dict(kind='wrong'), dict(extra=1), dict(requirements=[]),
                      dict(basis=[[[1, True]]]), dict(basis=[[[2, 1], [1, 1]]]),
                      dict(basis=[[[1, 1], [1, 2]]]), dict(basis=[[[1, 0]]]),
                      dict(basis=[[[3, 1]]]), dict(basis=[[]])]:
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                verify(example(), dict(certificate(), **patch))
        for patch in [dict(sign=True), dict(sign=-1), dict(required=True),
                      dict(required=0), dict(place=0), dict(target_row=True), dict(extra=1)]:
            c = certificate(); c['requirements'][0].update(patch)
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                verify(example(), c)
        for options in [dict(max_work=0), dict(deadline=time.monotonic())]:
            with self.assertRaises(TimeoutError): verify(example(), certificate(), **options)
        p = example(); p['transitions'][0]['pre'].append([0, 1])
        with self.assertRaises(ValueError): verify(p, certificate())

    def test_every_small_accepted_basis_is_unreachable(self):
        accepted = 0
        for initial in itertools.product(range(2), repeat=2):
            for pre in itertools.product(range(2), repeat=2):
                for post in itertools.product(range(2), repeat=2):
                    if sum(post) > sum(pre): continue
                    p = dict(places=['a', 'b'], initial=list(initial), transitions=[
                        dict(name='t', pre=[[i,x] for i,x in enumerate(pre) if x],
                             post=[[i,x] for i,x in enumerate(post) if x])],
                        target=[dict(coefficients=[1, -1], bound=1, equality=False)])
                    seen, pending = {initial}, [initial]
                    while pending:
                        marking = pending.pop()
                        if all(m>=w for m,w in zip(marking,pre)):
                            nxt = tuple(m-a+b for m,a,b in zip(marking,pre,post))
                            if nxt not in seen: seen.add(nxt);pending.append(nxt)
                    possible = [[], [[[0,1]]], [[[0,1]],[[1,1]]], [[[0,1]],[[1,2]]]]
                    for basis in possible:
                        c = dict(kind='backward-cover-v1', requirements=[
                            dict(target_row=0, sign=1, place=0, required=1)], basis=basis)
                        try: verify(p,c)
                        except ValueError: continue
                        accepted += 1
                        self.assertTrue(all(m[0]-m[1]<1 for m in seen))
        self.assertGreater(accepted,10)


if __name__ == '__main__': unittest.main()
