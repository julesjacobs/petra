import copy
import unittest

from benchmark import verify
from local_closure_checker import I64_MIN, project, verify_local_closure


def constraint(coefficients, bound, equality=False):
    return dict(coefficients=coefficients, bound=bound, equality=equality)


def certificate(places, thresholds, states):
    return dict(kind='local-closure-v1', places=places,
                closure=dict(kind='threshold-closure-v1', thresholds=thresholds, states=states))


def fixture():
    problem = dict(places=['p', 'q', 'external'], initial=[2, 0, 0], transitions=[
        dict(pre=[[0, 1]], post=[[1, 1]]),
        dict(pre=[[1, 1]], post=[[0, 1]]),
        dict(pre=[[2, 1]], post=[[2, 2]]),
    ], target=[constraint([1, 0, -1], 2), constraint([0, 1, 0], 1)])
    proof = certificate([0, 1], [3, 3], [[2, 0], [1, 1], [0, 2]])
    return problem, proof


class LocalClosureCheckerTests(unittest.TestCase):
    def reject(self, problem, proof):
        with self.assertRaises((AssertionError, KeyError, TypeError, ValueError)):
            verify_local_closure(problem, proof)

    def test_local_negative_certificate_and_dispatch(self):
        problem, proof = fixture()
        self.assertEqual(verify_local_closure(problem, proof), 'python-local-closure')
        self.assertEqual(verify(problem, dict(verdict='unreachable', proof=proof)), 'python-local-closure')
        with self.assertRaises(AssertionError):
            verify(problem, dict(verdict='reachable', trace=[], marking=problem['initial'], proof=proof))

    def test_omitted_positive_coefficient_cannot_create_a_false_local_target(self):
        problem = dict(places=['local', 'external'], initial=[0, 1], transitions=[],
                       target=[constraint([1, 1], 1)])
        proof = certificate([0], [2], [[0]])
        self.assertEqual(project(problem, [0])['target'], [])
        self.reject(problem, proof)
        problem['target'] = [constraint([1, 1], 1, equality=True)]
        self.assertEqual(project(problem, [0])['target'], [constraint([-1], -1)])
        self.reject(problem, proof)

    def test_every_omitted_coefficient_is_checked(self):
        problem = dict(places=['p', 'outside1', 'outside2'], initial=[0, 0, 2], transitions=[],
                       target=[constraint([1, -1, 1], 2)])
        self.assertEqual(project(problem, [0])['target'], [])
        self.reject(problem, certificate([0], [1], [[0]]))

    def test_equality_directions_are_independent_necessary_conditions(self):
        problem = dict(places=['p', 'q'], initial=[1, 0], transitions=[],
                       target=[constraint([1, -1], 2, equality=True)])
        self.assertEqual(project(problem, [0])['target'], [constraint([1], 2)])
        self.assertEqual(verify_local_closure(problem, certificate([0], [3], [[1]])), 'python-local-closure')
        problem['target'] = [constraint([-1, 1], -2, equality=True)]
        self.assertEqual(project(problem, [0])['target'], [constraint([1], 2)])
        self.assertEqual(verify_local_closure(problem, certificate([0], [3], [[1]])), 'python-local-closure')

    def test_i64_min_negation_skips_the_entire_negative_direction(self):
        problem = dict(places=['p', 'q'], initial=[0, 0], transitions=[],
                       target=[constraint([1, I64_MIN], 2, equality=True)])
        self.assertEqual(project(problem, [0])['target'], [constraint([1], 2)])
        self.assertEqual(project(problem, [0, 1])['target'], [constraint([1, I64_MIN], 2)])
        problem['target'] = [constraint([1, 0], I64_MIN, equality=True)]
        self.assertEqual(project(problem, [0])['target'], [constraint([1], I64_MIN)])
        self.reject(problem, certificate([0], [1], [[0]]))

    def test_transition_projection_deduplicates_and_keeps_weighted_guards(self):
        problem, proof = fixture()
        problem['transitions'].extend([
            dict(pre=[[2, 7], [0, 1]], post=[[2, 7], [1, 1]]),
            dict(pre=[[0, 2]], post=[[0, 2]]),
        ])
        projected = project(problem, [0, 1])
        self.assertEqual(len(projected['transitions']), 2)
        self.assertEqual(projected['transitions'][0]['pre'], ((0, 1),))
        self.assertEqual(verify_local_closure(problem, proof), 'python-local-closure')
        problem['transitions'].append(dict(pre=[[0, 2]], post=[[0, 2], [1, 1]]))
        self.reject(problem, proof)

    def test_forged_state_sets_thresholds_bounds_and_initial_marking(self):
        problem, proof = fixture()
        changed = copy.deepcopy(proof)
        changed['closure']['states'].pop()
        self.reject(problem, changed)
        changed = copy.deepcopy(proof)
        changed['closure']['states'] = [[2, 0]]
        self.reject(problem, changed)
        changed = copy.deepcopy(proof)
        changed['closure']['thresholds'] = [2, 3]
        self.reject(problem, changed)
        changed = copy.deepcopy(proof)
        changed['bound'] = 100
        self.reject(problem, changed)
        changed = copy.deepcopy(problem)
        changed['target'][0]['bound'] = 1
        self.reject(changed, proof)
        changed = copy.deepcopy(problem)
        changed['initial'] = [2, 1, 0]
        self.reject(changed, proof)

    def test_malformed_place_selection_and_certificate_schema(self):
        problem, proof = fixture()
        for places in ([1, 0], [0, 0], [-1], [3], [True], '0'):
            self.reject(problem, dict(proof, places=places))
        self.reject(problem, dict(proof, kind='projected-closure-v1'))
        self.reject(problem, dict(proof, target=[]))
        changed = copy.deepcopy(proof)
        changed['closure']['kind'] = 'wrong'
        self.reject(problem, changed)
        changed = copy.deepcopy(proof)
        changed['closure']['states'][0][0] = True
        self.reject(problem, changed)

    def test_empty_projection_can_refute_a_constant_necessary_condition(self):
        problem = dict(places=['p'], initial=[0], transitions=[dict(pre=[], post=[[0, 1]])],
                       target=[constraint([-1], 1)])
        self.assertEqual(verify_local_closure(problem, certificate([], [], [[]])), 'python-local-closure')
        problem['target'][0]['bound'] = 0
        self.reject(problem, certificate([], [], [[]]))


if __name__ == '__main__':
    unittest.main()
