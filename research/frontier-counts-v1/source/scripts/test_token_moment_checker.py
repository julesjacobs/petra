import copy
import json
from pathlib import Path
import unittest

from token_moment_checker import reconstruct_control, relaxation_rows, verify_token_moment

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    problem = dict(places=['a', 'b', 'data'], initial=[1, 0, 0],
                   transitions=[dict(pre=[[0, 1]], post=[[1, 1]])],
                   target=[dict(coefficients=[0, 0, 1], bound=1, equality=False)])
    proof = dict(kind='token-moment-v1', controls=[0, 1],
                 terminals=[[[4, '1'], [10, '1']], [[4, '1'], [10, '1']]])
    return problem, proof


class TokenMomentCheckerTests(unittest.TestCase):
    def reject(self, problem, proof):
        with self.assertRaises((AssertionError, KeyError, TypeError, ValueError, ZeroDivisionError)):
            verify_token_moment(problem, proof)

    def test_complete_negative_proof(self):
        problem, proof = fixture()
        self.assertEqual(verify_token_moment(problem, proof), 'python-token-moment')

    def test_rejects_malformed_leaves(self):
        problem, proof = fixture()
        for leaf in ([], [[4, '1']], [[10, '1']], [[4, '0'], [10, '1']],
                     [[4, '-1'], [10, '1']], [[4, '1/2'], [10, '1']],
                     [[4, '1'], [4, '1'], [10, '1']], [[10, '1'], [4, '1']],
                     [[4, '1'], [99999, '1']], [[4, '1/0'], [10, '1']],
                     [[4, 1], [10, '1']], [[True, '1'], [10, '1']]):
            changed = copy.deepcopy(proof)
            changed['terminals'][0] = leaf
            self.reject(problem, changed)

    def test_terminal_coverage_and_schema(self):
        problem, proof = fixture()
        for terminals in ([], proof['terminals'][:1], proof['terminals'] * 2):
            self.reject(problem, dict(proof, terminals=terminals))
        self.reject(problem, dict(proof, kind='wrong-kind'))
        self.reject(problem, dict(proof, cap=8192))

    def test_invalid_controls_and_conservation(self):
        problem, proof = fixture()
        for controls in ([], [0], [1], [0, 0], [1, 0], [0, 3], [False, 1]):
            self.reject(problem, dict(proof, controls=controls))
        changed = copy.deepcopy(problem)
        changed['initial'][1] = 1
        self.reject(changed, proof)
        changed = copy.deepcopy(problem)
        changed['transitions'][0]['post'] = [[1, 2]]
        self.reject(changed, proof)

    def test_changed_net_invalidates_proof(self):
        problem, proof = fixture()
        changed = copy.deepcopy(problem)
        changed['transitions'][0]['post'].append([2, 1])
        self.reject(changed, proof)
        changed = copy.deepcopy(problem)
        changed['transitions'].append(dict(pre=[], post=[[2, 1]]))
        self.reject(changed, proof)
        changed = copy.deepcopy(problem)
        changed['initial'][2] = 1
        self.reject(changed, proof)
        changed = copy.deepcopy(problem)
        changed['target'][0]['bound'] = 0
        self.reject(changed, proof)

    def test_original_input_validation(self):
        problem, proof = fixture()
        for arc in ([0, 0], [0, -1], [3, 1], [True, 1]):
            changed = copy.deepcopy(problem)
            changed['transitions'][0]['pre'] = [arc]
            self.reject(changed, proof)
        changed = copy.deepcopy(problem)
        changed['transitions'][0]['pre'] *= 2
        self.reject(changed, proof)
        changed = copy.deepcopy(problem)
        changed['target'][0]['coefficients'] = [1]
        self.reject(changed, proof)

    def test_graph_coverage_and_wire_order(self):
        problem = dict(places=['a', 'b', 'dead', 'data'], initial=[1, 0, 0, 0],
                       transitions=[dict(pre=[[0, 1], [3, 9]], post=[[1, 1]]),
                                    dict(pre=[[1, 1]], post=[[1, 1], [3, 2]]),
                                    dict(pre=[], post=[[3, 1]]),
                                    dict(pre=[[1, 2]], post=[[1, 2], [3, 1]]),
                                    dict(pre=[[0, 1], [1, 1]], post=[[0, 1], [1, 1]]),
                                    dict(pre=[[2, 1]], post=[[0, 1]])], target=[])
        modes, edges = reconstruct_control(problem, [0, 1, 2])
        self.assertEqual(modes, [0, 1])
        self.assertEqual(edges, [(0, 0, 2), (0, 1, 0), (1, 1, 2), (1, 1, 1)])
        problem['initial'] = [0, 0, 1, 0]
        modes, edges = reconstruct_control(problem, [0, 1, 2])
        self.assertEqual(modes, [2, 0, 1])
        self.assertEqual(edges[:2], [(0, 0, 2), (0, 1, 5)])

    def test_concrete_run_satisfies_every_row(self):
        problem = dict(places=['a', 'b', 'data'], initial=[1, 0, 1],
                       transitions=[dict(pre=[[2, 1]], post=[[2, 3]]),
                                    dict(pre=[[0, 1]], post=[[1, 1]]),
                                    dict(pre=[[1, 1], [2, 2]], post=[[0, 1], [2, 1]])],
                       target=[dict(coefficients=[0, 0, 1], bound=0, equality=False)])
        controls = [0, 1]
        modes, edges = reconstruct_control(problem, controls)
        for word in ([], [0], [1], [0, 1, 0, 2], [0, 0, 1, 2, 1, 2]):
            marking = problem['initial'][:]
            values = {}
            q = 0
            for t in word:
                e = next(e for e, (source, _, label) in enumerate(edges) if source == q and label == t)
                values['count', e] = values.get(('count', e), 0) + 1
                for p, tokens in enumerate(marking):
                    values['moment', e, p] = values.get(('moment', e, p), 0) + tokens
                transition = problem['transitions'][t]
                for p, w in transition['pre']:
                    self.assertGreaterEqual(marking[p], w)
                    marking[p] -= w
                for p, w in transition['post']:
                    marking[p] += w
                q = edges[e][1]
            for p, tokens in enumerate(marking):
                values['final', p] = tokens
            for terms, bound in relaxation_rows(problem, controls, modes, edges, q):
                self.assertGreaterEqual(sum(a * values.get(variable, 0) for variable, a in terms), bound)

    def test_g2_discovered_proof_and_mutations(self):
        with (ROOT / 'results/portfolio-larger-budget/g2_disjunct_1.json').open() as stream:
            problem = json.load(stream)
        with (ROOT / 'research/g2-token-moment.json').open() as stream:
            proof = json.load(stream)['proof']
        modes, edges = reconstruct_control(problem, proof['controls'])
        self.assertEqual((len(modes), len(edges)), (12, 202))
        self.assertEqual(verify_token_moment(problem, proof), 'python-token-moment')
        for terminal in range(len(modes)):
            changed = copy.deepcopy(proof)
            changed['terminals'][terminal] = changed['terminals'][terminal][:-1]
            self.reject(problem, changed)
        changed = copy.deepcopy(proof)
        changed['terminals'][0], changed['terminals'][1] = changed['terminals'][1], changed['terminals'][0]
        self.reject(problem, changed)


if __name__ == '__main__':
    unittest.main()
