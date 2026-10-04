import copy
import itertools
import unittest

from token_cut_checker import cut_row, master_rows, verify_token_cut
from token_moment_checker import reconstruct_control


def fixture():
    problem = dict(places=['a', 'b', 'data'], initial=[1, 0, 0],
                   transitions=[dict(pre=[[0, 1], [2, 1]], post=[[1, 1], [2, 1]]),
                                dict(pre=[[1, 1]], post=[[1, 1], [2, 1]])],
                   target=[dict(coefficients=[0, 1, 0], bound=1, equality=False)])
    proof = dict(kind='token-cut-v1', controls=[0, 1], terminals=[
        dict(cuts=[], multipliers=[[8, '1'], [10, '1']]),
        dict(cuts=[dict(place=2, modes=[1])],
             multipliers=[[2, '1'], [4, '1'], [10, '1'], [15, '1']])])
    return problem, proof


class TokenCutCheckerTests(unittest.TestCase):
    def reject(self, problem, proof):
        with self.assertRaises((AssertionError, KeyError, TypeError, ValueError, ZeroDivisionError)):
            verify_token_cut(problem, proof)

    def test_complete_cut_negative_proof(self):
        problem, proof = fixture()
        self.assertEqual(verify_token_cut(problem, proof), 'python-token-cut')

    def test_terminal_coverage_and_schema(self):
        problem, proof = fixture()
        for terminals in ([], proof['terminals'][:1], proof['terminals'] * 2):
            self.reject(problem, dict(proof, terminals=terminals))
        self.reject(problem, dict(proof, kind='wrong'))
        self.reject(problem, dict(proof, bound=10))
        changed = copy.deepcopy(proof)
        changed['terminals'][0]['ignored'] = True
        self.reject(problem, changed)

    def test_malformed_cuts_and_unbounded_outgoing_edge(self):
        problem, proof = fixture()
        for cut in (dict(place=2, modes=[0]), dict(place=2, modes=[1, 1]),
                    dict(place=2, modes=[1, 0]), dict(place=2, modes=[2]),
                    dict(place=3, modes=[1]), dict(place=True, modes=[1]),
                    dict(place=2, modes=[True]), dict(place=2, modes=[1], capacity=0)):
            changed = copy.deepcopy(proof)
            changed['terminals'][0]['cuts'] = [cut]
            self.reject(problem, changed)

    def test_forged_multipliers(self):
        problem, proof = fixture()
        for weights in ([], [[8, '1']], [[8, '-1'], [10, '1']],
                        [[8, '1'], [8, '1'], [10, '1']], [[10, '1'], [8, '1']],
                        [[8, '1'], [9999, '1']], [[8, '1/0'], [10, '1']],
                        [[8, 1], [10, '1']], [[True, '1'], [10, '1']]):
            changed = copy.deepcopy(proof)
            changed['terminals'][0]['multipliers'] = weights
            self.reject(problem, changed)

    def test_original_net_and_target_mutations(self):
        problem, proof = fixture()
        changed = copy.deepcopy(problem)
        changed['initial'][2] = 1
        self.reject(changed, proof)
        changed = copy.deepcopy(problem)
        changed['target'][0]['bound'] = 0
        self.reject(changed, proof)
        changed = copy.deepcopy(problem)
        changed['target'][0]['coefficients'] = [1, 0, 0]
        self.reject(changed, proof)
        changed = copy.deepcopy(problem)
        changed['transitions'][0]['pre'] = [[0, 1]]
        changed['transitions'][0]['post'] = [[1, 1]]
        self.reject(changed, proof)
        for controls in ([], [0], [1, 0], [0, 0], [0, 3], [False, 1]):
            self.reject(problem, dict(proof, controls=controls))

    def test_enabled_traces_satisfy_every_finite_cut(self):
        problem = dict(places=['a', 'b', 'data'], initial=[1, 0, 1],
                       transitions=[dict(pre=[[2, 1]], post=[[2, 3]]),
                                    dict(pre=[[0, 1]], post=[[1, 1]]),
                                    dict(pre=[[1, 1], [2, 2]], post=[[0, 1], [2, 1]])],
                       target=[dict(coefficients=[0, 0, 1], bound=0, equality=False)])
        controls = [0, 1]
        modes, edges = reconstruct_control(problem, controls)
        for length in range(5):
            for trace in itertools.product(range(3), repeat=length):
                marking, values, q = problem['initial'][:], {}, 0
                for t in trace:
                    transition = problem['transitions'][t]
                    if any(marking[p] < w for p, w in transition['pre']):
                        break
                    e = next(e for e, (source, _, label) in enumerate(edges) if source == q and label == t)
                    values['count', e] = values.get(('count', e), 0) + 1
                    for p, w in transition['pre']:
                        marking[p] -= w
                    for p, w in transition['post']:
                        marking[p] += w
                    q = edges[e][1]
                else:
                    for p, tokens in enumerate(marking):
                        values['final', p] = tokens
                    rows = list(master_rows(problem, controls, modes, edges, q))
                    for place in range(3):
                        for subset in ([], [0], [1], [0, 1]):
                            if place not in controls and any(s in subset and d not in subset for s, d, _ in edges):
                                continue
                            rows.append(cut_row(problem, controls, modes, edges, q,
                                                dict(place=place, modes=subset)))
                    for terms, bound in rows:
                        self.assertGreaterEqual(sum(a * values.get(variable, 0) for variable, a in terms), bound)


if __name__ == '__main__':
    unittest.main()
