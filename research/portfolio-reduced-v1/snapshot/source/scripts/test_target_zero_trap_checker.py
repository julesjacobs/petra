import copy
import itertools
import subprocess
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from target_zero_trap_checker import project, verify


def goal(coefficients, bound=0, equality=True):
    return dict(coefficients=coefficients, bound=bound, equality=equality)


def fixture():
    problem = dict(
        places=['trap', 'guard', 'target', 'other-trap'], initial=[0, 1, 0, 0],
        transitions=[
            dict(name='poison', pre=[], post=[[0, 1], [2, 3]]),
            dict(name='transfer-trap', pre=[[0, 7]], post=[[3, 1]]),
            dict(name='produce', pre=[[1, 1]], post=[[2, 1]]),
            dict(name='weighted-read', pre=[[3, 2]], post=[[3, 1], [2, 8]]),
            dict(name='retained-read', pre=[[1, 3]], post=[[1, 3]]),
        ],
        target=[goal([1, 0, 0, 4]), goal([0, 0, 1, 0], 2, False)])
    proof = dict(kind='target-zero-trap-v1', trap=[0, 3],
                 inner=dict(kind='threshold-closure-v1', thresholds=[2, 2], states=[[1, 0], [0, 1]]))
    return problem, proof


def check_inner(problem, proof):
    from benchmark import verify_proof
    return verify_proof(problem, proof)


class TargetZeroTrapTests(unittest.TestCase):
    def test_optimized_python_rejects_assertion_dependent_inner_proofs(self):
        code = '''from benchmark import verify_proof
p = dict(places=[], initial=[], transitions=[], target=[])
proof = dict(kind='target-zero-trap-v1', trap=[],
             inner=dict(kind='threshold-closure-v1', thresholds=[], states=[[]]))
try:
    verify_proof(p, proof)
except ValueError as error:
    if 'assertions enabled' not in str(error):
        raise
else:
    raise RuntimeError('accepted a certificate containing a target marking')
'''
        result = subprocess.run([sys.executable, '-O', '-c', code],
                                cwd=Path(__file__).resolve().parent,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def reject(self, problem, proof):
        callback = Mock(return_value='python-test')
        with self.assertRaises(ValueError):
            verify(problem, proof, callback)
        callback.assert_not_called()

    def test_independent_projection_and_dispatch(self):
        from benchmark import verify_proof, verify as verify_answer
        problem, proof = fixture()
        original = copy.deepcopy(problem)
        reduced = project(problem, proof['trap'])
        self.assertEqual(reduced, dict(
            places=['guard', 'target'], initial=[1, 0],
            transitions=[dict(name='produce', pre=[[0, 1]], post=[[1, 1]]),
                         dict(name='retained-read', pre=[[0, 3]], post=[[0, 3]])],
            target=[goal([0, 0]), goal([0, 1], 2, False)]))
        self.assertEqual(verify(problem, proof, check_inner), 'python-target-zero-trap')
        self.assertEqual(verify_proof(problem, proof), 'python-target-zero-trap')
        self.assertEqual(verify_answer(problem, dict(verdict='unreachable', proof=proof)), 'python-target-zero-trap')
        self.assertEqual(problem, original)

    def test_marked_weighted_trap_needs_post_support_not_nonnegative_incidence(self):
        from benchmark import verify_proof
        problem, _ = fixture()
        problem['initial'][0] = 7
        proof = dict(kind='target-zero-trap-marked-v1', trap=[0, 3])
        callback = Mock(side_effect=AssertionError('marked proof must not call inner checker'))
        self.assertEqual(verify(problem, proof, callback), 'python-target-zero-trap-marked')
        self.assertEqual(verify_proof(problem, proof), 'python-target-zero-trap-marked')
        callback.assert_not_called()
        problem['transitions'][1]['post'] = []
        self.reject(problem, proof)

    def test_marked_and_empty_proofs_are_not_interchangeable(self):
        problem, proof = fixture()
        self.reject(problem, dict(kind='target-zero-trap-marked-v1', trap=proof['trap']))
        problem['initial'][3] = 1
        self.reject(problem, proof)
        self.reject(problem, dict(kind='target-zero-trap-marked-v1', trap=[]))
        problem['initial'] = [0, 0, 9, 0]
        self.reject(problem, dict(kind='target-zero-trap-marked-v1', trap=[0, 3]))

    def test_forced_zero_signs_bounds_and_combined_constraints(self):
        problem = dict(places=['a', 'b'], initial=[0, 0], transitions=[], target=[])
        for constraint in [goal([1, 2]), goal([-1, -2]), goal([-1, -2], equality=False), goal([-2**63, -1])]:
            problem['target'] = [constraint]
            self.assertEqual(project(problem, [0, 1])['target'], [goal([], constraint['bound'], constraint['equality'])])
        for constraint in [goal([1, -1]), goal([1, -1], equality=False), goal([1, 2], equality=False),
                           goal([1, 2], 1), goal([-1, -2], -1, False), goal([0, 0]), goal([1, 0])]:
            problem['target'] = [constraint]
            with self.subTest(constraint=constraint), self.assertRaises(ValueError):
                project(problem, [0, 1])
        problem['target'] = [goal([1, 0]), goal([0, -2], equality=False), goal([3, -4], 7)]
        self.assertEqual(project(problem, [0, 1])['target'], [goal([]), goal([], equality=False), goal([], 7)])
        problem['target'] = [goal([0, 0], 1)]
        with self.assertRaises(ValueError):
            project(problem, [0])

    def test_self_loops_sources_and_siphon_trap_distinction(self):
        problem = dict(places=['trap', 'kept'], initial=[0, 0],
                       transitions=[dict(name='source', pre=[], post=[[0, 1]]),
                                    dict(name='read', pre=[[0, 2]], post=[[0, 2], [1, 1]])],
                       target=[goal([1, 0])])
        self.assertEqual(project(problem, [0])['transitions'], [])
        problem['transitions'] = [dict(name='drain', pre=[[0, 1]], post=[])]
        with self.assertRaisesRegex(ValueError, 'consuming transition'):
            project(problem, [0])
        problem['transitions'] = [dict(name='read', pre=[[0, 2]], post=[[0, 1]])]
        self.assertEqual(project(problem, [0])['transitions'], [])

    def test_nonmaximal_trap_and_preserved_order_weights_constant_rows(self):
        problem = dict(places=['kept-a', 'trap', 'kept-b', 'unused-zero'], initial=[2**64-1, 0, 1, 0],
                       transitions=[dict(name='retained', pre=[[2, 7], [0, 2]], post=[[0, 2], [2, 9]]),
                                    dict(name='removed', pre=[], post=[[1, 1]])],
                       target=[goal([0, 1, 0, 1]), goal([-2**63, 4, 7, 0], -2**63), goal([0, 0, 0, 0], 1)])
        reduced = project(problem, [1])
        self.assertEqual(reduced['places'], ['kept-a', 'kept-b', 'unused-zero'])
        self.assertEqual(reduced['transitions'], [dict(name='retained', pre=[[1, 7], [0, 2]], post=[[0, 2], [1, 9]])])
        self.assertEqual(reduced['target'], [goal([0, 0, 1]), goal([-2**63, 7, 0], -2**63), goal([0, 0, 0], 1)])

    def test_empty_trap_is_identity_and_requires_inner_negative(self):
        problem, _ = fixture()
        self.assertEqual(project(problem, []), problem)
        proof = dict(kind='target-zero-trap-v1', trap=[], inner={})
        for result in ('unknown', 'none', '', True, None, 1):
            with self.subTest(result=result), self.assertRaises(ValueError):
                verify(problem, proof, lambda p, c: result)
        with self.assertRaisesRegex(ValueError, 'forged'):
            verify(problem, proof, Mock(side_effect=ValueError('forged inner proof')))
        if __debug__:
            proof['inner'] = dict(kind='threshold-closure-v1', thresholds=[0]*4, states=[[0]*4])
            with self.assertRaises(AssertionError):
                verify(problem, proof, check_inner)
        zero = dict(places=[], initial=[], transitions=[], target=[goal([], 1)])
        proof['inner'] = dict(kind='threshold-closure-v1', thresholds=[], states=[[]])
        self.assertEqual(verify(zero, proof, check_inner), 'python-target-zero-trap')

    def test_malformed_proof_and_indices(self):
        problem, proof = fixture()
        for trap in ([3, 0], [0, 0], [-1], [4], [False], [0.0], '0', None):
            with self.subTest(trap=trap):
                self.reject(problem, dict(proof, trap=trap))
        for bad in (None, [], {}, dict(proof, kind='wrong'), dict(proof, inner=[]),
                    dict(proof, places=[1, 2]), dict(proof, reduced=problem),
                    dict(kind='target-zero-trap-v1', trap=[])):
            self.reject(problem, bad)
        self.reject(problem, dict(kind='target-zero-trap-marked-v1', trap=[0], inner={}))

    def test_every_original_field_and_removed_arc_is_validated(self):
        problem, proof = fixture()
        mutations = [
            lambda p: p.update(extra=True), lambda p: p.pop('target'),
            lambda p: p.update(places='abcd'), lambda p: p['places'].__setitem__(0, 0),
            lambda p: p.update(initial=[0]), lambda p: p['initial'].__setitem__(0, True),
            lambda p: p['initial'].__setitem__(0, -1), lambda p: p['initial'].__setitem__(0, 2**64),
            lambda p: p.update(transitions={}), lambda p: p['transitions'].__setitem__(0, []),
            lambda p: p['transitions'][0].update(extra=True), lambda p: p['transitions'][0].pop('name'),
            lambda p: p['transitions'][0].update(name=False), lambda p: p['transitions'][0].update(pre=()),
            lambda p: p['transitions'][0]['post'].append([0, 1]),
            lambda p: p['transitions'][0]['post'].__setitem__(0, (0, 1)),
            lambda p: p['transitions'][0]['post'].__setitem__(0, [0]),
            lambda p: p['transitions'][0]['post'].__setitem__(0, [False, 1]),
            lambda p: p['transitions'][0]['post'].__setitem__(0, [4, 1]),
            lambda p: p['transitions'][0]['post'].__setitem__(0, [-1, 1]),
            lambda p: p['transitions'][0]['post'].__setitem__(0, [0, False]),
            lambda p: p['transitions'][0]['post'].__setitem__(0, [0, 0]),
            lambda p: p['transitions'][0]['post'].__setitem__(0, [0, -1]),
            lambda p: p['transitions'][0]['post'].__setitem__(0, [0, 2**64]),
            lambda p: p.update(target={}), lambda p: p['target'].__setitem__(0, []),
            lambda p: p['target'][0].update(extra=True), lambda p: p['target'][0].pop('bound'),
            lambda p: p['target'][0].update(coefficients=[1]),
            lambda p: p['target'][0]['coefficients'].__setitem__(0, True),
            lambda p: p['target'][0]['coefficients'].__setitem__(0, 2**63),
            lambda p: p['target'][0]['coefficients'].__setitem__(0, -2**63-1),
            lambda p: p['target'][0].update(bound=True), lambda p: p['target'][0].update(bound=2**63),
            lambda p: p['target'][0].update(equality=1),
        ]
        for mutation in mutations:
            for marked in (False, True):
                bad = copy.deepcopy(problem)
                selected_proof = proof
                if marked:
                    bad['initial'][0] = 1
                    selected_proof = dict(kind='target-zero-trap-marked-v1', trap=[0, 3])
                mutation(bad)
                self.reject(bad, selected_proof)

    def test_budget_and_deadline_before_and_after_callback(self):
        problem, proof = fixture()
        for kwargs in (dict(max_work=0), dict(deadline=time.monotonic()-1)):
            callback = Mock(return_value='python-test')
            with self.assertRaises(TimeoutError):
                verify(problem, proof, callback, **kwargs)
            callback.assert_not_called()
        for kwargs in (dict(max_work=True), dict(max_work=-1), dict(deadline=float('nan')), dict(deadline=True)):
            with self.assertRaises(ValueError):
                verify(problem, proof, check_inner, **kwargs)
        with self.assertRaises(TimeoutError):
            verify(problem, proof, Mock(side_effect=TimeoutError('inner limit')))
        with patch('target_zero_trap_checker.time.monotonic', return_value=0) as clock:
            def expire(p, c):
                clock.return_value = 2
                return 'python-test'
            with self.assertRaises(TimeoutError):
                verify(problem, proof, expire, deadline=1)

    def test_mixed_wrappers_share_depth_and_deadline(self):
        from benchmark import verify_proof
        p = dict(places=['p'], initial=[0], transitions=[], target=[goal([1], 1)])
        inner = dict(kind='threshold-closure-v1', thresholds=[1], states=[[0]])
        for depth in range(32):
            if depth % 2:
                inner = dict(kind='relevance-v1', places=[0], transitions=[], inner=inner)
            else:
                inner = dict(kind='target-zero-trap-v1', trap=[], inner=inner)
        self.assertEqual(verify_proof(p, inner), 'python-relevance')
        with self.assertRaisesRegex(TimeoutError, 'nesting limit'):
            verify_proof(p, dict(kind='target-zero-trap-v1', trap=[], inner=inner))
        with self.assertRaisesRegex(TimeoutError, 'deadline'):
            verify_proof(p, inner, _relevance_deadline=time.monotonic()-1)
        wrapped = dict(kind='target-zero-trap-v1', trap=[], inner=dict(kind='relevance-v1', places=[0], transitions=[], inner=dict(kind='dag-cnf-rup-v1')))
        deadline = time.monotonic()+10
        with patch('dag_checker.verify', return_value='python-dag-cnf-rup') as callback:
            self.assertEqual(verify_proof(p, wrapped, _relevance_deadline=deadline, dag_max_work=123), 'python-target-zero-trap')
        self.assertEqual(callback.call_args.kwargs, dict(deadline=deadline, max_work=123))
        with patch('target_zero_trap_checker.time.monotonic', return_value=0) as clock:
            def expire(*args, **kwargs):
                clock.return_value=2
                return 'python-dag-cnf-rup'
            with patch('dag_checker.verify', side_effect=expire), self.assertRaises(TimeoutError):
                verify_proof(p, wrapped, _relevance_deadline=1)

    def test_32_wrappers_can_end_in_a_terminal_marked_proof(self):
        from benchmark import verify_proof
        problem = dict(places=['p'], initial=[1], transitions=[], target=[goal([1])])
        proof = dict(kind='target-zero-trap-marked-v1', trap=[0])
        for depth in range(32):
            if depth % 2:
                proof = dict(kind='relevance-v1', places=[0], transitions=[], inner=proof)
            else:
                proof = dict(kind='target-zero-trap-v1', trap=[], inner=proof)
        self.assertEqual(verify_proof(problem, proof), 'python-relevance')
        with self.assertRaisesRegex(TimeoutError, 'nesting limit'):
            verify_proof(problem, dict(kind='target-zero-trap-v1', trap=[], inner=proof))

    def test_successful_runs_cannot_use_removed_transitions(self):
        problem, proof = fixture()
        problem['target'][1]['bound'] = 1
        reduced = project(problem, proof['trap'])
        retained = [2, 4]
        successful = 0
        traces = itertools.chain.from_iterable(itertools.product(range(len(problem['transitions'])), repeat=length) for length in range(5))
        for trace in traces:
            original = problem['initial'][:]
            for tid in trace:
                tr = problem['transitions'][tid]
                if any(original[p] < w for p, w in tr['pre']):
                    break
                for p, w in tr['pre']:
                    original[p] -= w
                for p, w in tr['post']:
                    original[p] += w
            else:
                if original[0] or original[3] or original[2] < 1:
                    continue
                successful += 1
                projected = reduced['initial'][:]
                for tid in trace:
                    self.assertIn(tid, retained)
                    tr = reduced['transitions'][retained.index(tid)]
                    self.assertTrue(all(projected[p] >= w for p, w in tr['pre']))
                    for p, w in tr['pre']:
                        projected[p] -= w
                    for p, w in tr['post']:
                        projected[p] += w
                self.assertEqual(projected, [original[1], original[2]])
        self.assertGreater(successful, 0)


if __name__ == '__main__':
    unittest.main()
