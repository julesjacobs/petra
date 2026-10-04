import copy
import itertools
import subprocess
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from target_path_potential_checker import augment, verify


def row(coefficients, bound, equality=True):
    return dict(coefficients=coefficients, bound=bound, equality=equality)


def problem(step=2, target=1, initial=0):
    return dict(places=['p'], initial=[initial],
                transitions=[dict(name='grow', pre=[], post=[[0, step]])],
                target=[row([1], target)])


def proof():
    return dict(kind='target-path-potential-v1',
                inner=dict(kind='threshold-closure-v1', thresholds=[2, 2], states=[[0, 1]]))


def infeasible():
    return dict(kind='target-path-potential-infeasible-v1')


class TargetPathPotentialTests(unittest.TestCase):
    def reject(self, p, certificate):
        callback = Mock(return_value='python-test')
        with self.assertRaises(ValueError):
            verify(p, certificate, callback)
        callback.assert_not_called()

    def test_reconstruction_and_real_inner_proof(self):
        from benchmark import verify_proof, verify as verify_answer
        p = problem()
        saved = copy.deepcopy(p)
        expected = dict(places=['p', '__target_path_slack'], initial=[0, 1],
                        transitions=[dict(name='grow', pre=[[1, 2]], post=[[0, 2]])],
                        target=[row([1, 0], 1)])
        self.assertEqual(augment(p), expected)
        self.assertEqual(verify(p, proof(), verify_proof), 'python-target-path-potential')
        self.assertEqual(verify_answer(p, dict(verdict='unreachable', proof=proof())),
                         'python-target-path-potential')
        self.assertEqual(p, saved)
        if __debug__:
            with self.assertRaises(AssertionError):
                verify_proof(problem(step=1), proof())
            bad = proof()
            bad['inner']['states'] = [[0, 0]]
            with self.assertRaises(AssertionError):
                verify_proof(p, bad)

    def test_monotonicity_required_even_for_initial_infeasibility(self):
        from benchmark import verify_proof
        p = problem(initial=3, target=2)
        self.assertEqual(verify_proof(p, infeasible()), 'python-target-path-potential-infeasible')
        p['transitions'] = [dict(name='decrease', pre=[[0, 1]], post=[])]
        self.reject(p, infeasible())
        self.reject(p, proof())
        p['transitions'] = [dict(name='weighted-decrease', pre=[[0, 2]], post=[[0, 1]])]
        self.reject(p, infeasible())

    def test_flooring_both_equality_orientations_and_upper_inequality(self):
        p = problem()
        for coefficients, rhs, equality, expected in [([2], 7, True, 3),
                ([-2], -7, True, 3), ([-2], -7, False, 3),
                ([1], 0, True, 0), ([-2**63], -2**63, False, 1)]:
            p['target'] = [row(coefficients, rhs, equality)]
            self.assertEqual(augment(p)['initial'][-1], expected)
        for coefficients, rhs, equality in [([2], -1, True), ([-2], 1, True), ([-2], 1, False)]:
            p['target'] = [row(coefficients, rhs, equality)]
            self.assertEqual(verify(p, infeasible()), 'python-target-path-potential-infeasible')
            self.reject(p, proof())
        p['target'] = [row([2], 7, False)]
        self.reject(p, proof())
        p['target'] = [row([-1], -8, False), row([2], 7), row([-3], -8, False)]
        self.assertEqual(augment(p)['initial'][-1], 2)

    def test_sum_arithmetic_and_u64_representability(self):
        hi = 2**63 - 1
        p = dict(places=['a', 'b', 'c'], initial=[0, 0, 0],
                 transitions=[dict(name='grow', pre=[], post=[[0, 1]])],
                 target=[row([int(i == j) for i in range(3)], hi) for j in range(3)])
        self.reject(p, proof())
        p['target'][2]['bound'] = 1
        self.assertEqual(augment(p)['initial'][-1], 2**64-1)
        p['target'][2]['bound'] = 2
        self.reject(p, proof())
        p['initial'] = [hi, hi, 2]
        self.assertEqual(augment(p)['initial'][-1], 0)
        p['transitions'][0]['post'] = [[0, 2**64-1], [1, 1]]
        self.reject(p, proof())
        p['initial'][2] = 3
        self.assertEqual(verify(p, infeasible()), 'python-target-path-potential-infeasible')

    def test_preserves_arcs_rows_and_fresh_slack_name(self):
        p = dict(places=['__target_path_slack', '__target_path_slack_'], initial=[1, 1],
                 transitions=[dict(name='move', pre=[[1, 1]], post=[[0, 1]]),
                              dict(name='read-grow', pre=[[0, 1]], post=[[0, 1], [1, 2]])],
                 target=[row([1, 0], 4), row([0, -2], -8, False), row([1, -1], 0, False)])
        q = augment(p)
        self.assertEqual(q['places'][-1], '__target_path_slack__')
        self.assertEqual(q['initial'], [1, 1, 6])
        self.assertEqual(q['transitions'][0], p['transitions'][0])
        self.assertEqual(q['transitions'][1]['pre'], [[0, 1], [2, 2]])
        self.assertEqual(q['transitions'][1]['post'], [[0, 1], [1, 2]])
        self.assertEqual(q['target'], [row([1, 0, 0], 4), row([0, -2, 0], -8, False), row([1, -1, 0], 0, False)])

    def test_missing_bounds_and_no_growth_rejected(self):
        p = problem()
        for target in ([], [row([0], 0)], [row([1], 1, False)]):
            p['target'] = target
            self.reject(p, proof())
            self.reject(p, infeasible())
        p = problem()
        p['transitions'] = []
        self.reject(p, proof())
        p['initial'] = [2]
        self.assertEqual(verify(p, infeasible()), 'python-target-path-potential-infeasible')
        self.reject(dict(places=[], initial=[], transitions=[], target=[]), infeasible())
        self.reject(problem(target=1, initial=1), infeasible())

    def test_strict_proof_schema_and_checked_inner_required(self):
        for bad in (None, [], {}, dict(kind=False), dict(kind='wrong'),
                    dict(kind='target-path-potential-v1'), dict(proof(), inner=[]),
                    dict(proof(), weights=[1]), dict(proof(), bound=1),
                    dict(proof(), augmented=problem()), dict(infeasible(), inner={})):
            self.reject(problem(), bad)
        for value in (None, True, 1, '', 'unknown', 'none'):
            with self.assertRaises(ValueError):
                verify(problem(), proof(), lambda p, c: value)
        with self.assertRaisesRegex(ValueError, 'forged'):
            verify(problem(), proof(), Mock(side_effect=ValueError('forged inner proof')))

    def test_malformed_original_fields_checked_for_both_proof_forms(self):
        mutations = [lambda p: p.update(extra=True), lambda p: p.pop('target'),
            lambda p: p.update(places='p'), lambda p: p.update(places=[True]),
            lambda p: p.update(initial=[]), lambda p: p.update(initial=[True]),
            lambda p: p.update(initial=[-1]), lambda p: p.update(initial=[2**64]),
            lambda p: p.update(transitions={}), lambda p: p['transitions'][0].update(extra=1),
            lambda p: p['transitions'][0].update(name=1), lambda p: p['transitions'][0].update(pre=()),
            lambda p: p['transitions'][0]['post'].append([0, 1]),
            lambda p: p['transitions'][0].update(post=[[True, 1]]),
            lambda p: p['transitions'][0].update(post=[[1, 1]]),
            lambda p: p['transitions'][0].update(post=[[-1, 1]]),
            lambda p: p['transitions'][0].update(post=[[0, 0]]),
            lambda p: p['transitions'][0].update(post=[[0, True]]),
            lambda p: p['transitions'][0].update(post=[[0, 2**64]]),
            lambda p: p['transitions'][0].update(post=[[0, -1]]),
            lambda p: p['transitions'][0].update(post=[(0, 1)]),
            lambda p: p.update(target={}), lambda p: p['target'][0].update(extra=1),
            lambda p: p['target'][0].update(coefficients=[]),
            lambda p: p['target'][0].update(coefficients=[True]),
            lambda p: p['target'][0].update(coefficients=[2**63]),
            lambda p: p['target'][0].update(coefficients=[-2**63-1]),
            lambda p: p['target'][0].update(bound=True),
            lambda p: p['target'][0].update(bound=2**63),
            lambda p: p['target'][0].update(equality=1)]
        for i, mutation in enumerate(mutations):
            for impossible in (False, True):
                p = problem(initial=3 if impossible else 0)
                mutation(p)
                with self.subTest(mutation=i, impossible=impossible):
                    self.reject(p, infeasible() if impossible else proof())

    def test_limits_and_deadline_after_inner(self):
        for kwargs in (dict(max_work=0), dict(deadline=time.monotonic()-1)):
            callback = Mock(return_value='python-test')
            with self.assertRaises(TimeoutError):
                verify(problem(), proof(), callback, **kwargs)
            callback.assert_not_called()
        for kwargs in (dict(max_work=True), dict(max_work=-1), dict(deadline=float('nan')),
                       dict(deadline=float('inf')), dict(deadline=True)):
            with self.assertRaises(ValueError):
                verify(problem(), proof(), lambda p, c: 'python-test', **kwargs)
        with patch('target_path_potential_checker.time.monotonic', return_value=0) as clock:
            def expire(p, c):
                clock.return_value = 2
                return 'python-test'
            with self.assertRaises(TimeoutError):
                verify(problem(), proof(), expire, deadline=1)

    def test_shared_depth_and_deadline_with_other_wrappers(self):
        from benchmark import verify_proof
        certificate = proof()
        for depth in range(31):
            certificate = (dict(kind='target-zero-trap-v1', trap=[], inner=certificate)
                           if depth % 2 else
                           dict(kind='relevance-v1', places=[0], transitions=[0], inner=certificate))
        self.assertEqual(verify_proof(problem(), certificate), 'python-relevance')
        with self.assertRaisesRegex(TimeoutError, 'nesting limit'):
            verify_proof(problem(), dict(kind='target-zero-trap-v1', trap=[], inner=certificate))
        with self.assertRaises(TimeoutError):
            verify_proof(problem(), certificate, _relevance_deadline=time.monotonic()-1)
        terminal = infeasible()
        for _ in range(32):
            terminal = dict(kind='target-zero-trap-v1', trap=[], inner=terminal)
        self.assertEqual(verify_proof(problem(initial=2), terminal), 'python-target-zero-trap')
        deadline = time.monotonic()+10
        with patch('dag_checker.verify', return_value='python-dag-cnf-rup') as callback:
            wrapped = dict(kind='target-path-potential-v1', inner=dict(kind='dag-cnf-rup-v1'))
            verify_proof(problem(), wrapped, _relevance_deadline=deadline, dag_max_work=123)
        self.assertEqual(callback.call_args.kwargs, dict(deadline=deadline, max_work=123))

    def test_original_successful_traces_exactly_lift_with_slack(self):
        p = problem(step=1, target=3)
        p['transitions'].append(dict(name='grow-two', pre=[], post=[[0, 2]]))
        q = augment(p)
        successful = 0
        for length in range(5):
            for trace in itertools.product(range(2), repeat=length):
                marking = q['initial'][:]
                total = sum(p['transitions'][tid]['post'][0][1] for tid in trace)
                enabled = True
                for tid in trace:
                    t = q['transitions'][tid]
                    if any(marking[i] < w for i, w in t['pre']):
                        enabled = False
                        break
                    for i, w in t['pre']:
                        marking[i] -= w
                    for i, w in t['post']:
                        marking[i] += w
                    self.assertEqual(sum(marking), 3)
                self.assertEqual(enabled, total <= 3)
                if total == 3:
                    successful += 1
                    self.assertEqual(marking, [3, 0])
        self.assertGreater(successful, 0)

    def test_optimized_python_direct_checker_and_dispatch(self):
        code = '''from target_path_potential_checker import verify
from benchmark import verify_proof
p = dict(places=['p'], initial=[3], transitions=[dict(name='down', pre=[[0,1]], post=[])], target=[dict(coefficients=[1], bound=2, equality=True)])
proof = dict(kind='target-path-potential-infeasible-v1')
try:
    verify(p, proof)
except ValueError:
    pass
else:
    raise RuntimeError('accepted decreasing potential')
try:
    verify_proof(p, proof)
except ValueError as error:
    if 'assertions enabled' not in str(error):
        raise
else:
    raise RuntimeError('optimized dispatch permitted legacy inner checkers')
p['transitions'] = []
if verify(p, proof) != 'python-target-path-potential-infeasible':
    raise RuntimeError('valid terminal proof rejected')
'''
        result = subprocess.run([sys.executable, '-O', '-c', code],
                                cwd=Path(__file__).resolve().parent,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
