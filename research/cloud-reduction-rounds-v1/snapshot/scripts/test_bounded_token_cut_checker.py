import copy
import itertools
import unittest

from benchmark import verify
from bounded_token_cut_checker import verify_bounded_token_cut, verify_place_bounds
from token_cut_checker import cut_row, master_rows, verify_token_cut
from token_moment_checker import reconstruct_control


def certificate(*potentials):
    return dict(kind='place-bounds-v1', potentials=[dict(weights=w) for w in potentials])


def fixture():
    problem = dict(places=['a', 'b', 'data'], initial=[1, 0, 1],
                   transitions=[dict(pre=[[0, 1], [2, 2]], post=[[1, 1], [2, 2]]),
                                dict(pre=[[1, 1]], post=[[0, 1]])],
                   target=[dict(coefficients=[0, 1, 0], bound=1, equality=False)])
    proof = dict(kind='bounded-token-cut-v1', controls=[0, 1], bounds=certificate([[2, '1']]),
                 terminals=[dict(cuts=[], multipliers=[[8, '1'], [10, '1']]),
                            dict(cuts=[dict(place=2, modes=[1])],
                                 multipliers=[[4, '1'], [12, '2'], [15, '1']])])
    return problem, proof


class BoundedTokenCutCheckerTests(unittest.TestCase):
    def reject(self, problem, proof):
        with self.assertRaises((AssertionError, KeyError, TypeError, ValueError, ZeroDivisionError)):
            verify_bounded_token_cut(problem, proof)

    def test_bounded_cut_refutes_strongly_connected_control(self):
        problem, proof = fixture()
        self.assertEqual(verify_bounded_token_cut(problem, proof), 'python-bounded-token-cut')
        self.assertEqual(verify(problem, dict(verdict='unreachable', proof=proof)), 'python-bounded-token-cut')
        unbounded = {k: v for k, v in proof.items() if k != 'bounds'}
        unbounded['kind'] = 'token-cut-v1'
        with self.assertRaisesRegex(AssertionError, 'unbounded outgoing'):
            verify_token_cut(problem, unbounded)
        modes, edges = reconstruct_control(problem, proof['controls'])
        values = {('final', 0): 0, ('final', 1): 1, ('final', 2): 1,
                  ('count', 0): 1, ('count', 1): 0}
        for terms, bound in master_rows(problem, proof['controls'], modes, edges, 1):
            self.assertGreaterEqual(sum(a*values.get(v, 0) for v, a in terms), bound)

    def test_changed_initial_makes_target_reachable(self):
        problem, proof = fixture()
        problem['initial'][2] = 2
        self.reject(problem, proof)

    def test_increasing_transition_in_original_net_rejects_bound(self):
        problem, proof = fixture()
        problem['transitions'].append(dict(pre=[[0, 2]], post=[[0, 2], [2, 1]]))
        self.reject(problem, proof)

    def test_malformed_bounds_and_weights(self):
        problem, proof = fixture()
        bad = [dict(kind='wrong', potentials=[]), dict(kind='place-bounds-v1', potentials=[], upper=[1]),
               dict(kind='place-bounds-v1', potentials=[dict(weights=[[2, '1']], upper=1)]),
               dict(kind='place-bounds-v1', potentials=None)]
        for weights in ([], [[2, '-1']], [[2, '0']], [[2, '1/0']], [[2, 1]],
                        [[2, '1'], [2, '1']], [[2, '1'], [0, '1']], [[3, '1']], [[True, '1']]):
            bad.append(certificate(weights))
        for bounds in bad:
            self.reject(problem, dict(proof, bounds=bounds))
        self.reject(problem, dict(proof, bounds=certificate()))
        self.reject(problem, dict(proof, ignored=True))

    def test_forged_cut_or_multiplier(self):
        problem, proof = fixture()
        changed = copy.deepcopy(proof)
        changed['terminals'][1]['cuts'][0]['modes'] = [0]
        self.reject(problem, changed)
        changed = copy.deepcopy(proof)
        changed['terminals'][1]['multipliers'][1][1] = '1'
        self.reject(problem, changed)

    def test_exact_rational_floor_and_best_of_multiple_potentials(self):
        problem = dict(places=['p', 'q', 'r'], initial=[0, 1, 0], transitions=[], target=[])
        bound_proof = certificate([[0, '2/3'], [1, '1']], [[0, '1']], [[2, '1']])
        self.assertEqual(verify_place_bounds(problem, bound_proof), [0, 1, 0])
        bound_proof['potentials'].pop(1)
        self.assertEqual(verify_place_bounds(problem, bound_proof), [1, 1, 0])
        self.assertEqual(verify_place_bounds(problem, certificate([[0, '1']])), [0, None, None])

    def test_arbitrary_precision_bound(self):
        problem = dict(places=['p', 'q'], initial=[1, 1], transitions=[], target=[])
        huge = 2**200 + 1
        self.assertEqual(verify_place_bounds(problem, certificate([[0, '1'], [1, str(huge)]])),
                         [huge+1, 1])

    def test_enabled_traces_satisfy_all_bounded_cuts(self):
        problem = dict(places=['a', 'b', 'data', 'spare'], initial=[1, 0, 2, 1],
                       transitions=[dict(pre=[[0, 1], [2, 1]], post=[[1, 1], [3, 1]]),
                                    dict(pre=[[1, 1], [3, 1]], post=[[0, 1], [2, 1]]),
                                    dict(pre=[[2, 1]], post=[]),
                                    dict(pre=[[0, 1], [2, 4]], post=[[1, 1], [2, 4]])], target=[])
        controls = [0, 1]
        modes, edges = reconstruct_control(problem, controls)
        bounds = verify_place_bounds(problem, certificate([[2, '1'], [3, '1']]))
        self.assertEqual(bounds, [None, None, 3, 3])
        traces = 0
        for length in range(6):
            for trace in itertools.product(range(4), repeat=length):
                marking, values, q = problem['initial'][:], {}, 0
                for t in trace:
                    transition = problem['transitions'][t]
                    if any(marking[p] < w for p, w in transition['pre']):
                        break
                    e = next(e for e, (source, _, label) in enumerate(edges) if source == q and label == t)
                    values['count', e] = values.get(('count', e), 0)+1
                    for p, w in transition['pre']:
                        marking[p] -= w
                    for p, w in transition['post']:
                        marking[p] += w
                    q = edges[e][1]
                else:
                    traces += 1
                    for p, tokens in enumerate(marking):
                        values['final', p] = tokens
                    for place in range(4):
                        for subset in ([], [0], [1], [0, 1]):
                            terms, bound = cut_row(problem, controls, modes, edges, q,
                                                   dict(place=place, modes=subset), bounds)
                            self.assertGreaterEqual(sum(a*values.get(v, 0) for v, a in terms), bound)
        self.assertGreater(traces, 20)


if __name__ == '__main__':
    unittest.main()
