import copy
import unittest

from benchmark import verify_proof


def farkas(*rows):
    return dict(rule='farkas', multipliers=[[row, '1'] for row in rows])


def fixture():
    problem = dict(
        places=['a', 'b', 'goal'], initial=[1, 0, 0],
        transitions=[dict(pre=[[1, 2]], post=[[1, 2], [2, 1]]),
                     dict(pre=[[0, 1]], post=[[1, 2]])],
        target=[dict(coefficients=[1, 0, 0], bound=1, equality=True),
                dict(coefficients=[0, 0, 1], bound=1, equality=False)])
    proof = dict(kind='causal-state-equation-v1', root=dict(
        rule='support', places=[0], blocked=0,
        omit=farkas(5, 6), enter=farkas(4, 6)))
    return problem, proof


class CausalCheckerTests(unittest.TestCase):
    def reject(self, problem, proof):
        with self.assertRaises((AssertionError, KeyError, ValueError, TypeError, ZeroDivisionError)):
            verify_proof(problem, proof)

    def test_weighted_read_arcs_and_equality(self):
        problem, proof = fixture()
        self.assertEqual(verify_proof(problem, proof), 'python-causal-state-equation')
        proof['root']['enter'] = farkas(3, 6)
        self.reject(problem, proof)

    def test_invalid_support(self):
        problem, proof = fixture()
        for places in ([], [0, 0], [1], [0, 3], [-1, 0], [2, 0], [False], [0, 1, 2]):
            bad = copy.deepcopy(proof)
            bad['root']['places'] = places
            self.reject(problem, bad)
        for blocked in (-1, 1, 2, True):
            bad = copy.deepcopy(proof)
            bad['root']['blocked'] = blocked
            self.reject(problem, bad)

    def test_invalid_leaves(self):
        problem, proof = fixture()
        for multipliers in ([], [[5, '1']], [[6, '1']], [[5, '-1'], [6, '1']],
                            [[5, '0'], [6, '1']], [[5, '1'], [5, '1'], [6, '1']],
                            [[6, '1'], [5, '1']], [[5, '1'], [7, '1']],
                            [[5, '1'], [6, '1/2']], [[5, '1'], [6, 1]],
                            [[True, '1']], [[5, '1/0'], [6, '1']]):
            bad = copy.deepcopy(proof)
            bad['root']['omit']['multipliers'] = multipliers
            self.reject(problem, bad)
        for child in ('omit', 'enter'):
            bad = copy.deepcopy(proof)
            del bad['root'][child]
            self.reject(problem, bad)

    def test_frontier_includes_all_original_transitions(self):
        problem, proof = fixture()
        problem['transitions'].append(dict(pre=[], post=[[1, 2]]))
        self.reject(problem, proof)
        problem['transitions'][-1] = dict(pre=[[0, 1]], post=[[0, 1], [1, 2]])
        self.reject(problem, proof)

    def test_ancestors_and_siblings(self):
        problem, proof = fixture()
        proof['root']['omit'] = dict(rule='support', places=[0], blocked=0,
                                    omit=farkas(5, 7), enter=farkas(5, 6))
        self.assertEqual(verify_proof(problem, proof), 'python-causal-state-equation')
        bad = copy.deepcopy(proof)
        bad['root']['omit']['enter'] = farkas(5, 7)
        self.reject(problem, bad)
        bad = copy.deepcopy(proof)
        bad['root']['enter'] = farkas(5, 6)
        self.reject(problem, bad)

    def test_initial_marking_and_transition_mutations(self):
        problem, proof = fixture()
        for initial in ([1, 2, 0], [1, 0, 1]):
            bad = copy.deepcopy(problem)
            bad['initial'] = initial
            self.reject(bad, proof)
        bad = copy.deepcopy(problem)
        bad['transitions'][1]['post'].append([0, 1])
        self.reject(bad, proof)

    def test_empty_frontier(self):
        problem = dict(places=['b', 'goal'], initial=[0, 0],
                       transitions=[dict(pre=[[0, 1]], post=[[0, 1], [1, 1]])],
                       target=[dict(coefficients=[0, 1], bound=1, equality=False)])
        proof = dict(kind='causal-state-equation-v1', root=dict(
            rule='support', places=[], blocked=0, omit=farkas(2, 3), enter=farkas(3)))
        self.assertEqual(verify_proof(problem, proof), 'python-causal-state-equation')

    def test_root_farkas(self):
        problem = dict(places=['p'], initial=[2], transitions=[],
                       target=[dict(coefficients=[1], bound=1, equality=True)])
        proof = dict(kind='causal-state-equation-v1', root=farkas(1))
        self.assertEqual(verify_proof(problem, proof), 'python-causal-state-equation')
        proof['root'] = farkas(2)
        self.reject(problem, proof)


if __name__ == '__main__':
    unittest.main()
