import copy
import itertools
import time
import unittest
from unittest.mock import Mock, patch

from relevance_checker import project, verify


def fixture():
    problem = dict(
        places=['guard', 'target', 'unused'], initial=[1, 0, 3],
        transitions=[dict(name='produce', pre=[[0, 1]], post=[[1, 1]]),
                     dict(name='discard-guard', pre=[[0, 1], [2, 1]], post=[]),
                     dict(name='unused-source', pre=[], post=[[2, 1]]),
                     dict(name='weighted-read', pre=[[0, 3], [2, 1]], post=[[0, 3], [2, 2]])],
        target=[dict(coefficients=[0, 1, 0], bound=2, equality=False)])
    proof = dict(kind='relevance-v1', places=[0, 1], transitions=[0],
                 inner=dict(kind='threshold-closure-v1', thresholds=[2, 2], states=[[1, 0], [0, 1]]))
    return problem, proof


def inner_check(problem, proof):
    from benchmark import verify_proof
    return verify_proof(problem, proof)


class RelevanceTests(unittest.TestCase):
    def test_benchmark_dispatch_and_bounded_nested_wrappers(self):
        from benchmark import verify_proof
        problem, proof = fixture()
        self.assertEqual(verify_proof(problem, proof), 'python-relevance')
        reduced = project(problem, proof['places'], proof['transitions'])
        nested = proof['inner']
        for _ in range(32):
            nested = dict(kind='relevance-v1', places=[0, 1], transitions=[0], inner=nested)
        self.assertEqual(verify_proof(reduced, nested), 'python-relevance')
        nested = dict(kind='relevance-v1', places=[0, 1], transitions=[0], inner=nested)
        with self.assertRaisesRegex(TimeoutError, 'nesting limit'):
            verify_proof(reduced, nested)

    def test_nested_dag_receives_shared_deadline_and_explicit_work_limit(self):
        from benchmark import verify_proof
        problem, proof = fixture()
        proof['inner'] = dict(kind='relevance-v1', places=[0, 1], transitions=[0],
                             inner=dict(kind='dag-cnf-rup-v1', control_places=[0, 1], additions=[[]]))
        deadline = time.monotonic() + 10
        with patch('dag_checker.verify', return_value='python-dag-cnf-rup') as callback:
            verify_proof(problem, proof, dag_max_work=7_000_000, _relevance_deadline=deadline)
        self.assertEqual(callback.call_args.kwargs, dict(deadline=deadline, max_work=7_000_000))

    def test_legacy_farkas_adapter_inside_relevance_wrapper(self):
        from benchmark import verify_proof
        problem, proof = fixture()
        proof['inner'] = dict(kind='state-equation-v1', certificate=['0', '1', '0', '1'])
        if not __debug__:
            with self.assertRaisesRegex(ValueError, 'assertions enabled'):
                verify_proof(problem, proof)
            return
        self.assertEqual(verify_proof(problem, proof), 'python-relevance')
        for inner in (dict(proof['inner'], trusted=True),
                      dict(kind='state-equation-v1'),
                      dict(kind='state-equation-v1', certificate='0 1 0 1'),
                      dict(kind='state-equation-v1', certificate=[])):
            bad = dict(proof, inner=inner)
            with self.assertRaises(ValueError): verify_proof(problem, bad)
        bad = dict(proof, inner=dict(kind='state-equation-v1', certificate=['0', '0', '0', '0']))
        with self.assertRaises(AssertionError): verify_proof(problem, bad)

    def test_checked_negative_and_independent_projection(self):
        problem, proof = fixture()
        self.assertEqual(verify(problem, proof, inner_check), 'python-relevance')
        original = copy.deepcopy(problem)
        reduced = project(problem, proof['places'], proof['transitions'])
        self.assertEqual(reduced, dict(places=['guard', 'target'], initial=[1, 0],
                                      transitions=[problem['transitions'][0]],
                                      target=[dict(coefficients=[0, 1], bound=2, equality=False)]))
        self.assertEqual(problem, original)

    def test_preserves_weighted_arcs_signed_targets_and_original_order(self):
        problem = dict(places=['drop', 'a', 'b', 'c'], initial=[2**64-1, 0, 1, 0],
                       transitions=[dict(name='weighted', pre=[[3, 7], [1, 2]], post=[[2, 9], [1, 2], [0, 100]])],
                       target=[dict(coefficients=[0, -2**63, 4, 0], bound=-2**63, equality=True)])
        result = project(problem, [1, 2, 3], [0])
        self.assertEqual(result['transitions'][0], dict(name='weighted', pre=[[2, 7], [0, 2]], post=[[1, 9], [0, 2]]))
        self.assertEqual(result['target'], [dict(coefficients=[-2**63, 4, 0], bound=-2**63, equality=True)])

    def test_rejects_guard_target_and_transition_omission_forgeries(self):
        problem, proof = fixture()
        for places, transitions in (([1], [0]), ([0], [0]), ([0, 1], []), ([], [])):
            with self.subTest(places=places, transitions=transitions), self.assertRaises(ValueError):
                project(problem, places, transitions)
        for arcs in (([[1, 1]], []), ([], [[0, 1]])):
            bad = copy.deepcopy(problem)
            bad['transitions'][1]['pre'], bad['transitions'][1]['post'] = arcs
            with self.assertRaises(ValueError): project(bad, proof['places'], proof['transitions'])
        problem['target'][0]['coefficients'] = [-1, 1, 0]
        with self.assertRaisesRegex(ValueError, 'changes target'):
            project(problem, proof['places'], proof['transitions'])

    def test_ordered_unique_exact_mapping_indices(self):
        problem, proof = fixture()
        for places in ([1, 0], [0, 0, 1], [False, 1], [-1, 0, 1], [0, 1, 3], [0.0, 1], '01'):
            with self.subTest(places=places), self.assertRaises(ValueError): project(problem, places, [0])
        for transitions in ([0, 0], [1, 0], [True], [4], [-1], [0.0], '0'):
            with self.subTest(transitions=transitions), self.assertRaises(ValueError): project(problem, [0, 1], transitions)

    def test_original_schema_is_validated_before_inner_proof(self):
        problem, proof = fixture()
        mutations = [lambda p: p['initial'].__setitem__(0, True),
                     lambda p: p['transitions'][2]['post'].append([2, 1]),
                     lambda p: p['transitions'][2]['post'].__setitem__(0, [3, 1]),
                     lambda p: p['transitions'][2]['post'].__setitem__(0, [2, 0]),
                     lambda p: p['transitions'][2]['post'].__setitem__(0, [2, 2**64]),
                     lambda p: p['target'][0]['coefficients'].__setitem__(0, True),
                     lambda p: p['target'][0].__setitem__('bound', 2**63),
                     lambda p: p['target'][0].__setitem__('equality', 1)]
        for mutation in mutations:
            bad = copy.deepcopy(problem)
            mutation(bad)
            check = Mock(return_value='python-test')
            with self.assertRaises(ValueError): verify(bad, proof, check)
            check.assert_not_called()

    def test_wrapper_and_inner_verification_cannot_be_forged(self):
        problem, proof = fixture()
        for field, value in (('kind', 'other'), ('inner', []), ('reduced', problem)):
            bad = dict(proof, **{field: value})
            with self.assertRaises(ValueError): verify(problem, bad, inner_check)
        for unchecked in ('none', 'unknown', '', True, None):
            with self.assertRaises(ValueError): verify(problem, proof, lambda p, c: unchecked)
        with self.assertRaisesRegex(ValueError, 'forged'):
            verify(problem, proof, Mock(side_effect=ValueError('forged inner proof')))

    def test_empty_projection_and_constant_targets(self):
        problem, _ = fixture()
        problem['target'] = [dict(coefficients=[0, 0, 0], bound=1, equality=True)]
        self.assertEqual(project(problem, [], []), dict(places=[], initial=[], transitions=[],
                                                       target=[dict(coefficients=[], bound=1, equality=True)]))

    def test_resource_limits_apply_before_and_after_inner_check(self):
        problem, proof = fixture()
        for kwargs in (dict(max_work=0), dict(deadline=time.monotonic()-1)):
            callback = Mock(return_value='python-test')
            with self.assertRaises(TimeoutError): verify(problem, proof, callback, **kwargs)
            callback.assert_not_called()
        with self.assertRaises(TimeoutError):
            verify(problem, proof, Mock(side_effect=TimeoutError('inner limit')))
        with patch('relevance_checker.time.monotonic', return_value=0) as clock:
            def expire(p, c):
                clock.return_value = 2
                return 'python-test'
            with self.assertRaises(TimeoutError): verify(problem, proof, expire, deadline=1)

    def test_projected_execution_simulates_omitted_consumption(self):
        problem, proof = fixture()
        reduced = project(problem, proof['places'], proof['transitions'])
        for sequence in itertools.product(range(4), repeat=4):
            original = problem['initial'][:]
            projected = reduced['initial'][:]
            for tid in sequence:
                tr = problem['transitions'][tid]
                if any(original[p] < w for p, w in tr['pre']): break
                for p, w in tr['pre']: original[p] -= w
                for p, w in tr['post']: original[p] += w
                if tid in proof['transitions']:
                    tr = reduced['transitions'][proof['transitions'].index(tid)]
                    self.assertTrue(all(projected[p] >= w for p, w in tr['pre']))
                    for p, w in tr['pre']: projected[p] -= w
                    for p, w in tr['post']: projected[p] += w
                self.assertGreaterEqual(projected[0], original[0])
                self.assertEqual(projected[1], original[1])


if __name__ == '__main__':
    unittest.main()
