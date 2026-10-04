#!/usr/bin/env python3
"""Independent finite-schedule model and artifact tests; not a SER interpreter."""
from collections import deque
import itertools
import json
from pathlib import Path
import tempfile
import unittest

import generate_transfer_ser_v2 as generator


def initial(sites, requests):
    return False, (0,) * sites, (-1,) * sites, (0,) * len(requests), (None,) * len(requests)


def step(state, requests, index, strict):
    ready, occupied, owners, pcs, responses = state
    if pcs[index] == 2:
        return None
    occupied, owners, pcs, responses = map(list, (occupied, owners, pcs, responses))
    kind, *endpoints = requests[index]
    if kind == 'seed':
        if not ready:
            occupied[0] = occupied[len(occupied) // 2] = 1
        ready = True
        responses[index], pcs[index] = 0, 2
    else:
        if not ready:
            return None
        resources = sorted(endpoints) if kind == 'transfer' else list(range(len(occupied)))
        for place in resources:
            if owners[place] not in (-1, index):
                changed = (ready, tuple(occupied), tuple(owners), tuple(pcs), tuple(responses))
                return changed if changed != state else None
            owners[place] = index
        if kind == 'count':
            responses[index], pcs[index] = sum(occupied), 2
        elif pcs[index] == 0:
            source, target = endpoints
            if occupied[source] and not occupied[target]:
                occupied[source] = 0
                pcs[index] = 1
            else:
                responses[index], pcs[index] = 0, 2
        else:
            occupied[endpoints[1]] = 1
            responses[index], pcs[index] = 1, 2
        if pcs[index] == 2 or not strict:
            for place in resources:
                owners[place] = -1
    return ready, tuple(occupied), tuple(owners), tuple(pcs), tuple(responses)


def histories(sites, requests, strict):
    first = initial(sites, requests)
    queue, seen, completed = deque([first]), {first}, set()
    while queue:
        state = queue.popleft()
        if all(pc == 2 for pc in state[3]):
            completed.add(state[4])
        for index in range(len(requests)):
            following = step(state, requests, index, strict)
            if following is not None and following not in seen:
                seen.add(following)
                queue.append(following)
    return completed, seen


def serial_responses(sites, requests):
    results = set()
    for order in itertools.permutations(range(len(requests))):
        ready, occupied, responses = False, set(), [None] * len(requests)
        for index in order:
            kind, *edge = requests[index]
            if kind == 'seed':
                if not ready:
                    occupied = {0, sites // 2}
                ready, responses[index] = True, 0
            elif not ready:
                break
            elif kind == 'count':
                responses[index] = len(occupied)
            else:
                source, target = edge
                moved = source in occupied and target not in occupied
                if moved:
                    occupied.remove(source)
                    occupied.add(target)
                responses[index] = int(moved)
        else:
            results.add(tuple(responses))
    return results


class TransferSources(unittest.TestCase):
    def test_fixed_ladder_graphs_and_matching_pairs(self):
        cases = list(generator.cases())
        self.assertEqual(len(cases), 12)
        by_name = {c['name']: c for c in cases}
        for case in cases:
            other = by_name[case['paired_with']]
            self.assertEqual(other['paired_with'], case['name'])
            self.assertNotEqual(case['serializable'], other['serializable'])
            self.assertEqual(case['parameters']['undirected_edges'], other['parameters']['undirected_edges'])
            self.assertEqual(len(case['parameters']['initial_occupied']), 2)
        for n in [4, 6]:
            path, cycle, chorded = [set(generator.edges(n, t)) for t in generator.TOPOLOGIES]
            self.assertLess(path, cycle)
            self.assertLess(cycle, chorded)
            self.assertEqual(len(chorded), n + n // 2)
            self.assertTrue(all((i, i + n // 2) in chorded for i in range(n // 2)))

    def test_generated_lock_scope_and_seed_are_explicit(self):
        for n in [4, 6]:
            strict = generator.program(n, 'path', True)
            unsafe = generator.program(n, 'path', False)
            for text in [strict, unsafe]:
                seed = text.split('request transfer', 1)[0]
                self.assertNotIn('yield', seed)
                self.assertIn(f'Occupied{n // 2} := 1; Ready := 1', seed)
                self.assertIn('while (Ready == 0) { yield }', text)
                self.assertIn('Lock0 := 0;\n    answer', text)
            transfer = lambda s: s.split('request transfer0to1 {', 1)[1].split('\n}\n', 1)[0]
            self.assertIn('Occupied0 := 0; yield; Occupied1 := 1', transfer(strict))
            self.assertIn('Occupied0 := 0; Lock1 := 0; Lock0 := 0; yield;', transfer(unsafe))
            self.assertEqual(transfer(unsafe).count('Lock0 := 1'), 2)
            self.assertEqual(transfer(strict).count('Lock0 := 1'), 1)

    def test_unsafe_witness_is_completed_and_has_no_serial_explanation(self):
        for n in [4, 6]:
            requests = [('seed',), ('transfer', 0, 1), ('count',)]
            state = initial(n, requests)
            for actor in [0, 1, 2, 1]:
                state = step(state, requests, actor, False)
                self.assertIsNotNone(state)
            self.assertEqual(state[3], (2, 2, 2))
            self.assertEqual(state[4], (0, 1, 1))
            self.assertNotIn(state[4], serial_responses(n, requests))

    def test_seed_blocks_operations_and_repeated_seed_does_not_reset(self):
        requests = [('count',), ('transfer', 0, 1), ('seed',), ('seed',)]
        state = initial(4, requests)
        self.assertIsNone(step(state, requests, 0, True))
        self.assertIsNone(step(state, requests, 1, True))
        for actor in [2, 1, 3, 1]:
            state = step(state, requests, actor, True)
        self.assertEqual(state[1], (0, 1, 1, 0))
        self.assertEqual(state[4][1:], (1, 0, 0))

    def test_strict_interleavings_match_serial_histories(self):
        for n in [4, 6]:
            edges = generator.edges(n, 'chorded')
            directed = edges + [(b, a) for a, b in edges]
            for first in directed:
                for second in directed:
                    requests = [('seed',), ('transfer', *first), ('transfer', *second), ('count',)]
                    completed, states = histories(n, requests, True)
                    self.assertTrue(completed)
                    self.assertLessEqual(completed, serial_responses(n, requests))
                    self.assertTrue(all(s[4][3] in (None, 2) for s in states))
                    self.assertTrue(all(all(owner == -1 for owner in s[2]) for s in states if all(pc == 2 for pc in s[3])))

    def test_artifacts_are_deterministic_hashed_and_unproved(self):
        files = generator.artifacts()
        self.assertEqual(files, generator.artifacts())
        manifest = json.loads(files['manifest.json'])
        self.assertEqual(manifest['format'], 'ser-stress-sources-v1')
        self.assertEqual(len({c['sha256'] for c in manifest['cases']}), 12)
        self.assertEqual(sum(c['feasibility_bridge'] for c in manifest['cases']), 6)
        for case in manifest['cases']:
            self.assertEqual(case['sha256'], generator.digest(files[case['source']]))
            self.assertFalse(case['source_expectation']['mechanically_verified'])
            self.assertIsNone(case['export_result'])
            self.assertIsNone(case['solver_result'])
        for line in files['SHA256SUMS'].decode().splitlines():
            digest, name = line.split('  ')
            self.assertEqual(digest, generator.digest(files[name]))

    def test_freeze_refuses_mutation_without_overwriting(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'sources'
            self.assertTrue(generator.freeze(output))
            self.assertFalse(generator.freeze(output))
            (output / 'transfer_n4_path_strict.ser').write_text('changed')
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            with self.assertRaises(ValueError):
                generator.freeze(output)
            self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})

    def test_invalid_parameters(self):
        for n in [True, 0, 3, 5, 8]:
            with self.assertRaises(ValueError):
                generator.program(n, 'path', True)
        with self.assertRaises(ValueError):
            generator.program(4, 'complete', True)
        with self.assertRaises(ValueError):
            generator.program(4, 'path', 1)


if __name__ == '__main__':
    unittest.main()
