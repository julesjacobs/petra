import copy
import time
import json
import tempfile
from pathlib import Path
import unittest
from raw_schema_check import verify


def fixture():
    q = dict(format='ser-raw-v2', places=['response', 'pending'], initial=[0, 1],
             transitions=[dict(name='finish', pre=[[1, 1]], post=[[0, 2]])],
             target=dict(kind='completed-outside-automaton', zero_places=[1], response_places=[0],
                         excluded_automaton=dict(states=2, initial=0, accepting=[0], edges=[
                             dict(source=0, target=1, response=0),dict(source=1, target=0, response=0)])))
    proof = dict(format='raw-automaton-invariant-v1',
                 schemas=[dict(segments=[dict(path=[], cycles=[[0, 1]])])],
                 invariant=dict(format='raw-component-invariant-v1', control_places=[],
                                credits=[dict(place=1, terms=[[0, 2]])], initial_node=0,
                                initial_coefficients=[[0, 1]],
                                nodes=[dict(control=[], component=0, edges=[])]))
    return q, proof


class SchemaTests(unittest.TestCase):
    def test_parent_recognizes_checked_schema_proof(self):
        from benchmark_stress_raw import classify_worker
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'result.json').write_text(json.dumps(dict(verdict='unreachable',
                status='verified-negative', independent_check='python-raw-automaton-invariant')))
            self.assertEqual(classify_worker(root, 0, False, {})['verdict'], 'unreachable')

    def test_checked_sublanguage_and_original_net(self):
        q, proof = fixture()
        self.assertEqual(verify(q, proof, time.monotonic()+2), 'python-raw-automaton-invariant')
        q['transitions'][0]['post'] = [[0, 1]]
        with self.assertRaises(ValueError):
            verify(q, proof, time.monotonic()+2)

    def test_forged_paths_cycles_endpoints_and_limits(self):
        q, proof = fixture()
        for cycle in [[0], [1, 0], [2], [], [True]]:
            bad = copy.deepcopy(proof)
            bad['schemas'][0]['segments'][0]['cycles'] = [cycle]
            with self.assertRaises(ValueError):
                verify(q, bad, time.monotonic()+2)
        q['target']['excluded_automaton']['accepting'] = [1]
        with self.assertRaises(ValueError):
            verify(q, proof, time.monotonic()+2)
        q, proof = fixture()
        with self.assertRaises(TimeoutError):
            verify(q, proof, time.monotonic()+2, 0)
        with self.assertRaises(TimeoutError):
            verify(q, proof, time.monotonic())


if __name__ == '__main__': unittest.main()
