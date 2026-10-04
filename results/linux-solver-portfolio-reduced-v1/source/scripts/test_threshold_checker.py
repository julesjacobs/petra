import copy
import unittest

from benchmark import verify


def problem(initial, transitions, coefficients, bound, equality=True):
    return dict(places=[f'p{i}' for i in range(len(initial))], initial=initial,
                transitions=[dict(pre=pre, post=post) for pre,post in transitions],
                target=[dict(coefficients=coefficients, bound=bound, equality=equality)])


def answer(thresholds, states):
    return dict(verdict='unreachable', proof=dict(kind='threshold-closure-v1',
                thresholds=thresholds, states=states))


class ThresholdCheckerTests(unittest.TestCase):
    def test_unbounded_increasing_place(self):
        net = problem([1], [([], [(0,1)])], [1], 0)
        self.assertEqual(verify(net, answer([1], [[1]])), 'python-threshold-closure')

    def test_decrement_must_exit_high_bucket(self):
        net = problem([2,0], [([(0,1)], [])], [0,1], 1)
        with self.assertRaises(AssertionError):
            verify(net, answer([2,1], [[2,0]]))
        verify(net, answer([2,1], [[2,0],[1,0],[0,0]]))

    def test_read_arc_enables_at_high_bucket(self):
        net = problem([1], [([(0,3)], [(0,3)])], [1], 0)
        verify(net, answer([1], [[1]]))

    def test_read_arc_disables_exact_bucket(self):
        net = problem([1], [([(0,3)], [(0,4)])], [1], 2)
        verify(net, answer([2], [[1]]))

    def test_signed_unbounded_target(self):
        net = problem([0], [], [-1], -3, False)
        with self.assertRaises(AssertionError):
            verify(net, answer([0], [[0]]))
        net['target'][0]['bound'] = 1
        verify(net, answer([0], [[0]]))

    def test_equality_checks_lower_and_upper(self):
        net = problem([2], [], [1], 1)
        verify(net, answer([2], [[2]]))
        net['target'][0]['bound'] = 3
        with self.assertRaises(AssertionError):
            verify(net, answer([2], [[2]]))

    def test_conjunction_preserves_overapproximation(self):
        net = problem([0], [], [1], 0)
        net['target'].append(dict(coefficients=[1], bound=1, equality=True))
        with self.assertRaises(AssertionError):
            verify(net, answer([0], [[0]]))

    def test_cartesian_successors(self):
        net = problem([1,1,0], [([(0,1),(1,1)], [])], [0,0,1], 1)
        valid = answer([1,1,1], [[a,b,0] for a in range(2) for b in range(2)])
        verify(net, valid)
        invalid = copy.deepcopy(valid)
        invalid['proof']['states'].remove([0,1,0])
        with self.assertRaises(AssertionError):
            verify(net, invalid)

    def test_missing_initial(self):
        with self.assertRaises(AssertionError):
            verify(problem([0], [], [1], 2), answer([2], [[1]]))

    def test_malformed_states(self):
        net = problem([0], [], [1], 2)
        for certificate in [answer([], [[]]), answer([1], [[0,0]]),
                            answer([1], [[2]]), answer([True], [[0]]),
                            answer([1], [[False]]), answer([-1], [[0]])]:
            with self.subTest(certificate=certificate), self.assertRaises(AssertionError):
                verify(net, certificate)


if __name__ == '__main__':
    unittest.main()
