import copy
import subprocess
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from buffer_agglomeration_checker import reconstruct, verify


def row(coefficients, bound, equality=True):
    return dict(coefficients=coefficients, bound=bound, equality=equality)


def transition(name, pre=(), post=()):
    return dict(name=name, pre=[list(arc) for arc in pre], post=[list(arc) for arc in post])


def step(place=1, orientation='eager'):
    return dict(place=place, orientation=orientation)


def fixture():
    p = dict(places=['source', 'buffer', 'out', 'goal'], initial=[1, 0, 0, 0],
             transitions=[transition('produce', [(0, 1)], [(1, 2), (3, 1)]),
                          transition('consume', [(1, 2)], [(2, 3)])],
             target=[row([0, 0, 0, 1], 2)])
    proof = dict(kind='buffer-agglomeration-v1', steps=[step()],
                 inner=dict(kind='threshold-closure-v1', thresholds=[2, 4, 3],
                            states=[[1, 0, 0], [0, 3, 1]]))
    return p, proof


def reachable(p, depth):
    initial = tuple(p['initial'])
    states, frontier = {initial}, {initial}
    for _ in range(depth):
        new = set()
        for marking in frontier:
            for t in p['transitions']:
                if any(marking[i] < w for i, w in t['pre']):
                    continue
                after = list(marking)
                for i, w in t['pre']:
                    after[i] -= w
                for i, w in t['post']:
                    after[i] += w
                new.add(tuple(after))
        frontier = new-states
        states |= new
    return states


class BufferAgglomerationTests(unittest.TestCase):
    def reject(self, p, proof):
        callback = Mock(return_value='python-test')
        with self.assertRaises(ValueError):
            verify(p, proof, callback)
        callback.assert_not_called()

    def test_eager_reconstruction_real_inner_proof_and_dispatch(self):
        from benchmark import verify_proof, verify as verify_answer
        p, proof = fixture()
        before = copy.deepcopy(p)
        self.assertEqual(reconstruct(p, proof['steps']), dict(
            places=['source', 'out', 'goal'], initial=[1, 0, 0],
            transitions=[transition('buffer-macro-2', [(0, 1)], [(1, 3), (2, 1)])],
            target=[row([0, 0, 1], 2)]))
        self.assertEqual(verify(p, proof, verify_proof), 'python-buffer-agglomeration')
        self.assertEqual(verify_proof(p, proof), 'python-buffer-agglomeration')
        self.assertEqual(verify_answer(p, dict(verdict='unreachable', proof=proof)), 'python-buffer-agglomeration')
        self.assertEqual(p, before)
        if __debug__:
            p['target'][0]['bound'] = 1
            with self.assertRaises(AssertionError):
                verify_proof(p, proof)

    def test_delayed_merges_inputs_and_preserves_consumer_output_order(self):
        from benchmark import verify_proof
        p = dict(places=['source', 'buffer', 'goal', 'other'], initial=[1, 0, 0, 2],
                 transitions=[transition('produce', [(3, 1), (0, 1)], [(1, 2)]),
                              transition('consume', [(1, 2), (3, 1)], [(3, 1), (2, 1)])],
                 target=[row([0, 0, 1, 0], 2)])
        proof = dict(kind='buffer-agglomeration-v1', steps=[step(1, 'delayed')],
                     inner=dict(kind='threshold-closure-v1', thresholds=[2, 3, 3], states=[[1, 0, 2], [0, 1, 1]]))
        q = reconstruct(p, proof['steps'])
        self.assertEqual(q['transitions'], [transition('buffer-macro-2', [(0, 1), (2, 2)], [(2, 1), (1, 1)])])
        self.assertEqual(verify_proof(p, proof), 'python-buffer-agglomeration')
        self.reject(p, dict(proof, steps=[step(1, 'eager')]))

    def test_stable_ids_repeated_steps_and_cartesian_order_without_dedup(self):
        p = dict(places=['a', 'b', 'keep'], initial=[0, 0, 0], transitions=[
            transition('source1', [], [(0, 2)]), transition('source2', [], [(0, 2)]),
            transition('bridge', [(0, 2)], [(1, 3)]), transition('finish', [(1, 3)], [(2, 1)]),
            transition('untouched', [(2, 2)], [(2, 2)])], target=[row([0, 0, 0], 1)])
        q = reconstruct(p, [step(0), step(1)])
        self.assertEqual(q, dict(places=['keep'], initial=[0], transitions=[
            transition('untouched', [(0, 2)], [(0, 2)]),
            transition('buffer-macro-7', [], [(0, 1)]), transition('buffer-macro-8', [], [(0, 1)])],
            target=[row([0], 1)]))
        alternative = reconstruct(p, [step(1, 'delayed'), step(0)])
        self.assertEqual([t['name'] for t in alternative['transitions']], ['untouched', 'buffer-macro-6', 'buffer-macro-7'])
        proof = dict(kind='buffer-agglomeration-v1', steps=[step(0), step(0)], inner={})
        self.reject(p, proof)

    def test_all_pairs_sorted_ids_not_names_and_original_arc_order(self):
        p = dict(places=['s0', 'p', 's1'], initial=[1, 0, 1], transitions=[
            transition('z', [(2, 1), (0, 1)], [(1, 1)]), transition('a', [], [(1, 1)]),
            transition('z-consumer', [(1, 1)], [(2, 1)]), transition('a-consumer', [(1, 1)], [(0, 1)])], target=[])
        q = reconstruct(p, [step()])
        self.assertEqual(q['transitions'], [
            transition('buffer-macro-4', [(1, 1), (0, 1)], [(1, 1)]),
            transition('buffer-macro-5', [(1, 1), (0, 1)], [(0, 1)]),
            transition('buffer-macro-6', [], [(1, 1)]),
            transition('buffer-macro-7', [], [(0, 1)])])

    def test_direction_target_and_incidence_guards(self):
        p, proof = fixture()
        for mutation in [lambda p: p['initial'].__setitem__(1, 2),
                         lambda p: p['target'][0]['coefficients'].__setitem__(1, 1),
                         lambda p: p['target'][0]['coefficients'].__setitem__(2, -1),
                         lambda p: p['transitions'][1]['pre'].append([0, 1]),
                         lambda p: p['transitions'][1]['post'].append([1, 2]),
                         lambda p: p['transitions'][0]['post'].__setitem__(0, [1, 3]),
                         lambda p: p['transitions'].pop(0),
                         lambda p: p['transitions'].pop(1)]:
            bad = copy.deepcopy(p)
            mutation(bad)
            self.reject(bad, proof)
        delayed = dict(places=['input', 'p', 'goal'], initial=[1, 0, 0], transitions=[
            transition('produce', [(0, 1)], [(1, 1)]), transition('consume', [(1, 1)], [(2, 1)])],
            target=[row([0, 0, 1], 1)])
        dproof = dict(kind='buffer-agglomeration-v1', steps=[step(1, 'delayed')], inner={})
        for mutation in [lambda p: p['transitions'][0]['post'].append([0, 1]),
                         lambda p: p['target'][0]['coefficients'].__setitem__(0, -1)]:
            bad = copy.deepcopy(delayed)
            mutation(bad)
            self.reject(bad, dproof)

    def test_forbidden_target_coordinates_have_real_counterexamples(self):
        eager = dict(places=['p', 'queried', 'goal'], initial=[0, 0, 0], transitions=[
            transition('f', [], [(0, 1), (2, 1)]), transition('c', [(0, 1)], [(1, 1)])],
            target=[row([0, 1, 0], 0), row([0, 0, 1], 1)])
        delayed = dict(places=['queried', 'p', 'goal'], initial=[1, 0, 0], transitions=[
            transition('f', [(0, 1)], [(1, 1)]), transition('c', [(1, 1)], [(2, 1)])],
            target=[row([1, 0, 0], 0), row([0, 0, 1], 0)])
        self.reject(eager, dict(kind='buffer-agglomeration-v1', steps=[step(0)], inner={}))
        self.reject(delayed, dict(kind='buffer-agglomeration-v1', steps=[step(1, 'delayed')], inner={}))
        self.assertIn((1, 0, 1), reachable(eager, 1))
        self.assertIn((0, 1, 0), reachable(delayed, 1))
        unsafe_eager = dict(places=['queried', 'goal'], initial=[0, 0], transitions=[
            transition('fc', [], [(0, 1), (1, 1)])])
        unsafe_delayed = dict(places=['queried', 'goal'], initial=[1, 0], transitions=[
            transition('fc', [(0, 1)], [(1, 1)])])
        self.assertNotIn((0, 1), reachable(unsafe_eager, 3))
        self.assertNotIn((0, 0), reachable(unsafe_delayed, 3))

    def test_many_steps_fit_linear_incidence_work_budget(self):
        count = 512
        p = dict(places=['source']+[f'p{i}' for i in range(count)]+['goal'],
                 initial=[1]+[0]*(count+1),
                 transitions=[transition(f'move{i}', [(i, 1)], [(i+1, 1)]) for i in range(count+1)],
                 target=[row([0]*(count+1)+[1], 2)])
        steps = [step(i, 'eager' if i < count else 'delayed') for i in range(1, count+1)]
        reduced = reconstruct(p, steps, max_work=100_000)
        self.assertEqual(reduced, dict(places=['source', 'goal'], initial=[1, 0],
            transitions=[transition('buffer-macro-1024', [(0, 1)], [(1, 1)])], target=[row([0, 1], 2)]))

    def test_exact_arc_arithmetic_overflow_and_tombstone_caps(self):
        p, proof = fixture()
        p['transitions'][0]['post'].append([2, 2**64-4])
        q = reconstruct(p, proof['steps'])
        self.assertEqual(q['transitions'][0]['post'][0], [1, 2**64-1])
        p['transitions'][0]['post'][-1][1] += 1
        self.reject(p, proof)
        p, proof = fixture()
        with patch('buffer_agglomeration_checker.MAX_STABLE_ARCS', 8):
            self.assertEqual(len(reconstruct(p, proof['steps'])['transitions']), 1)
        with patch('buffer_agglomeration_checker.MAX_STABLE_ARCS', 7):
            self.reject(p, proof)
        with patch('buffer_agglomeration_checker.MAX_STABLE_TRANSITIONS', 2):
            self.reject(p, proof)
        with patch('buffer_agglomeration_checker.MAX_STABLE_TRANSITIONS', 3):
            self.assertEqual(len(reconstruct(p, proof['steps'])['transitions']), 1)

    def test_original_large_cartesian_growth_rejected_before_inner(self):
        p = dict(places=['p'], initial=[0], target=[], transitions=[
            transition('f', [], [(0, 1)]) for _ in range(33)] + [
            transition('c', [(0, 1)], []) for _ in range(33)])
        self.reject(p, dict(kind='buffer-agglomeration-v1', steps=[step(0)], inner={}))

    def test_strict_schema_and_actual_integer_types(self):
        p, proof = fixture()
        for bad in (None, [], {}, dict(proof, extra=1), dict(proof, kind='wrong'),
                    dict(proof, inner=None), dict(proof, steps=[]), dict(proof, steps='1'),
                    dict(proof, steps=[dict(step(), transitions=[])]),
                    dict(proof, steps=[dict(place=1)])):
            self.reject(p, bad)
        for place in (-1, 4, True, 1.0, '1'):
            self.reject(p, dict(proof, steps=[step(place)]))
        for orientation in (False, None, 'Eager', 'both'):
            self.reject(p, dict(proof, steps=[step(1, orientation)]))
        mutations = [lambda p: p.update(extra=1), lambda p: p.update(places='p'),
            lambda p: p['places'].__setitem__(0, False), lambda p: p.update(initial=[0]),
            lambda p: p['initial'].__setitem__(0, True), lambda p: p['initial'].__setitem__(0, -1),
            lambda p: p['initial'].__setitem__(0, 2**64), lambda p: p.update(transitions={}),
            lambda p: p['transitions'][0].update(extra=1), lambda p: p['transitions'][0].update(name=True),
            lambda p: p['transitions'][0].update(pre=()), lambda p: p['transitions'][0].update(pre=[[0]]),
            lambda p: p['transitions'][0].update(pre=[(0, 1)]),
            lambda p: p['transitions'][0]['post'].append([1, 2]),
            lambda p: p['transitions'][0]['post'].__setitem__(0, [True, 2]),
            lambda p: p['transitions'][0]['post'].__setitem__(0, [4, 2]),
            lambda p: p['transitions'][0]['post'].__setitem__(0, [1, True]),
            lambda p: p['transitions'][0]['post'].__setitem__(0, [1, 0]),
            lambda p: p['transitions'][0]['post'].__setitem__(0, [1, 2**64]),
            lambda p: p.update(target={}), lambda p: p['target'][0].update(extra=1),
            lambda p: p['target'][0].update(coefficients=[]), lambda p: p['target'][0].update(bound=True),
            lambda p: p['target'][0].update(bound=2**63), lambda p: p['target'][0].update(equality=1),
            lambda p: p['target'][0]['coefficients'].__setitem__(0, True),
            lambda p: p['target'][0]['coefficients'].__setitem__(0, -2**63-1)]
        for i, mutation in enumerate(mutations):
            bad = copy.deepcopy(p)
            mutation(bad)
            with self.subTest(mutation=i):
                self.reject(bad, proof)

    def test_limits_callback_and_input_immutability_on_rejection(self):
        p, proof = fixture()
        original = copy.deepcopy(p)
        for kwargs in (dict(max_work=0), dict(max_work=10), dict(deadline=time.monotonic()-1)):
            callback = Mock(return_value='python-test')
            with self.assertRaises(TimeoutError):
                verify(p, proof, callback, **kwargs)
            callback.assert_not_called()
        for kwargs in (dict(max_work=True), dict(max_work=-1), dict(deadline=True), dict(deadline=float('inf'))):
            with self.assertRaises(ValueError):
                verify(p, proof, lambda p, c: 'python-test', **kwargs)
        for result in (None, True, '', 'unknown', 1):
            with self.assertRaises(ValueError):
                verify(p, proof, lambda p, c: result)
        with patch('buffer_agglomeration_checker.time.monotonic', return_value=0) as clock:
            def expire(p, c):
                clock.return_value = 2
                return 'python-test'
            with self.assertRaises(TimeoutError):
                verify(p, proof, expire, deadline=1)
        self.assertEqual(p, original)

    def test_packet_commutation_on_cyclic_shared_input_output_net(self):
        p = dict(places=['a', 'b', 'p', 'goal'], initial=[1, 0, 0, 0], transitions=[
            transition('f-a', [(0, 1)], [(2, 2), (3, 1)]),
            transition('f-b', [(1, 1)], [(2, 2), (3, 2)]),
            transition('c-a', [(2, 2)], [(0, 1)]),
            transition('c-b', [(2, 2)], [(1, 1)]),
            transition('read-a', [(0, 1)], [(0, 1)])], target=[row([0, 0, 0, 1], 2)])
        q = reconstruct(p, [step(2)])
        original = reachable(p, 6)
        reduced = reachable(q, 6)
        self.assertTrue({m[3] for m in original} <= {m[2] for m in reduced})
        self.assertTrue({m[2] for m in reachable(q, 3)} <= {m[3] for m in original})
        reversed_net = dict(places=p['places'], initial=[1, 0, 0, 6],
                            transitions=[transition(t['name'], t['post'], t['pre']) for t in p['transitions']],
                            target=p['target'])
        reverse_reduced = reconstruct(reversed_net, [step(2, 'delayed')])
        reverse_original = reachable(reversed_net, 6)
        self.assertTrue({m[3] for m in reverse_original} <= {m[2] for m in reachable(reverse_reduced, 6)})
        self.assertTrue({m[2] for m in reachable(reverse_reduced, 3)} <= {m[3] for m in reverse_original})

    def test_nesting_shared_deadline_and_optimized_python(self):
        from benchmark import verify_proof
        p, proof = fixture()
        for _ in range(31):
            proof = dict(kind='target-zero-trap-v1', trap=[], inner=proof)
        self.assertEqual(verify_proof(p, proof), 'python-target-zero-trap')
        with self.assertRaisesRegex(TimeoutError, 'nesting limit'):
            verify_proof(p, dict(kind='target-zero-trap-v1', trap=[], inner=proof))
        with self.assertRaises(TimeoutError):
            verify_proof(p, proof, _relevance_deadline=time.monotonic()-1)
        code = '''from buffer_agglomeration_checker import reconstruct
from benchmark import verify_proof
p = dict(places=['p'], initial=[1], transitions=[], target=[])
try:
    reconstruct(p, [dict(place=0, orientation='eager')])
except ValueError:
    pass
else:
    raise RuntimeError('accepted marked buffer')
try:
    verify_proof(p, dict(kind='buffer-agglomeration-v1', steps=[], inner={}))
except ValueError as error:
    if 'assertions enabled' not in str(error):
        raise
else:
    raise RuntimeError('optimized dispatch enabled')
'''
        result = subprocess.run([sys.executable, '-O', '-c', code],
                                cwd=Path(__file__).resolve().parent, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)


if __name__ == '__main__':
    unittest.main()
