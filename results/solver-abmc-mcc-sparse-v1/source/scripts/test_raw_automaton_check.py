import copy
import itertools
import json
from pathlib import Path
import tempfile
import time
import unittest

from raw_automaton_check import member
from raw_stress_worker import validate, verify_positive


def query(automaton):
    return dict(format='ser-raw-v2', places=['a', 'b'], initial=[0, 0], transitions=[],
                target=dict(kind='completed-outside-automaton', zero_places=[],
                            response_places=[0, 1], excluded_automaton=automaton))


class AutomatonTests(unittest.TestCase):
    def test_bounded_parent_accepts_only_recognized_verification(self):
        from benchmark_stress_raw import classify_worker
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for label, expected in [('python-original-replay-z3-connected-flow-nonmembership', 'reachable'),
                                    ('unchecked', 'unknown')]:
                (root / 'result.json').write_text(json.dumps(dict(
                    verdict='reachable', status='verified-positive', independent_check=label)))
                self.assertEqual(classify_worker(root, 0, False, {})['verdict'], expected)

    def test_connected_flow_matches_explicit_words(self):
        for seed in range(16):
            a = dict(states=3, initial=seed % 3,
                     accepting=[s for s in range(3) if seed & (1 << s)],
                     edges=[dict(source=i // 3, target=i % 3, response=(seed+i) % 2)
                            for i in range(9) if (seed*17+i*13) % 5 < 2])
            validate(query(a))
            frontier = [(a['initial'], (0, 0))]
            parikh = set()
            for length in range(5):
                following = []
                for state, counts in frontier:
                    if state in a['accepting']:
                        parikh.add(counts)
                    if length < 4:
                        for edge in a['edges']:
                            if edge['source'] == state:
                                c = list(counts)
                                c[edge['response']] += 1
                                following.append((edge['target'], tuple(c)))
                frontier = following
            for counts in itertools.product(range(3), repeat=2):
                self.assertEqual(member(a, [0, 1], counts, time.monotonic()+2), counts in parikh)

    def test_disconnected_cycle_is_not_serial(self):
        a = dict(states=2, initial=0, accepting=[0],
                 edges=[dict(source=1, target=1, response=0)])
        self.assertFalse(member(a, [0, 1], [1, 0], time.monotonic()+2))
        q = query(a)
        q['initial'] = [1, 0]
        self.assertEqual(verify_positive(q, dict(verdict='reachable', trace=[], marking=[1, 0]),
                                        time.monotonic()+2),
                         'python-original-replay-z3-connected-flow-nonmembership')
        q['initial'] = [0, 0]
        with self.assertRaisesRegex(ValueError, 'belongs'):
            verify_positive(q, dict(verdict='reachable', trace=[], marking=[0, 0]), time.monotonic()+2)

    def test_limits_and_invalid_schema(self):
        q = query(dict(states=1, initial=0, accepting=[0], edges=[]))
        with self.assertRaises(TimeoutError):
            member(q['target']['excluded_automaton'], [0, 1], [0, 0], time.monotonic())
        for bad in [True, -1, 1]:
            invalid = copy.deepcopy(q)
            invalid['target']['excluded_automaton']['initial'] = bad
            with self.assertRaises(ValueError):
                validate(invalid)


if __name__ == '__main__':
    unittest.main()
