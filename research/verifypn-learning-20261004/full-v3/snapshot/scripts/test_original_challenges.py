import unittest

from build_original_challenges import select_views


class ChallengeTests(unittest.TestCase):
    def report(self):
        return dict(stable_solved={'native': 1, 'external': 1}, cases=[
            dict(query='intermittent', verdicts=dict(native=['reachable', 'unknown'], external=['reachable', 'reachable'])),
            dict(query='unsolved', verdicts=dict(native=['unknown', 'error'], external=['unknown', 'unknown'])),
            dict(query='negative', verdicts=dict(native=['unreachable', 'unreachable'], external=['unknown', 'unknown'])),
        ])

    def test_intermittent_answer_is_not_jointly_unresolved(self):
        self.assertEqual(select_views(self.report(), 'native', ['external']), {
            'candidate-not-stable': ['intermittent', 'unsolved'],
            'competitor-only': ['intermittent'], 'joint-unresolved': ['unsolved']})

    def test_reject_invalid_comparators(self):
        for candidate, others in [('absent', ['external']), ('native', []), ('native', ['native']), ('native', ['absent'])]:
            with self.assertRaises(ValueError):
                select_views(self.report(), candidate, others)


if __name__ == '__main__':
    unittest.main()
