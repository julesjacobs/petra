import copy
import itertools
import unittest

from finite_token_cut_checker import (
    checked_bounds, cut_row, master_rows, reconstruct, validate_problem,
    verify_finite_token_cut,
)


def fixture():
    return dict(places=['x', 'y', 'z'], initial=[2, 0, 1], transitions=[
        dict(name='forward', pre=[[0, 1]], post=[[1, 1]]),
        dict(name='backward', pre=[[1, 1]], post=[[0, 1]]),
        dict(name='read', pre=[[2, 1]], post=[[2, 1]]),
        dict(name='disabled', pre=[[0, 3]], post=[[0, 3]]),
    ], target=[])


def bounds():
    return dict(kind='place-bounds-v1', potentials=[
        dict(weights=[[0, '1'], [1, '1']]), dict(weights=[[2, '1']])])


def negative():
    problem = dict(places=['x'], initial=[2], transitions=[
        dict(name='consume', pre=[[0, 1]], post=[])
    ], target=[dict(coefficients=[1], bound=3, equality=False)])
    proof = dict(kind='finite-token-cut-v1', controls=[0],
                 bounds=dict(kind='place-bounds-v1', potentials=[dict(weights=[[0, '1']])]),
                 terminals=[dict(cuts=[], multipliers=[[2, '1'], [4, '1']]) for _ in range(3)])
    return problem, proof


class CheckerTests(unittest.TestCase):
    def test_accepts_multitoken_and_empty_projection_proofs(self):
        problem, proof = negative()
        self.assertEqual(verify_finite_token_cut(problem, proof), 'python-finite-token-cut')
        from benchmark import verify
        self.assertEqual(verify(problem, dict(verdict='unreachable', proof=proof)),
                         'python-finite-token-cut')
        proof['controls'] = []
        proof['terminals'] = [dict(cuts=[], multipliers=[[0, '1'], [2, '1']])]
        self.assertEqual(verify_finite_token_cut(problem, proof), 'python-finite-token-cut')

    def test_graph_preserves_weighted_reads_stutter_and_bound_filter(self):
        problem = fixture()
        finite = checked_bounds(problem, bounds())
        modes, edges = reconstruct(problem, [0, 1], finite)
        self.assertEqual(modes, [(2, 0), (1, 1), (0, 2)])
        self.assertEqual(edges, [(0, 1, 0), (0, 0, 2), (1, 2, 0),
                                 (1, 0, 1), (1, 1, 2), (2, 1, 1), (2, 2, 2)])
        single_modes, single_edges = reconstruct(problem, [0], finite)
        self.assertEqual(single_modes, [(2,), (1,), (0,)])
        self.assertEqual(single_edges, edges)

    def test_all_rows_hold_on_concrete_prefixes(self):
        problem = fixture()
        finite = checked_bounds(problem, bounds())
        for controls in ([], [0], [0, 1], [0, 2]):
            modes, edges = reconstruct(problem, controls, finite)
            modes_index = {state: q for q, state in enumerate(modes)}
            edges_index = {edge: e for e, edge in enumerate(edges)}
            frontier = [(problem['initial'], [0] * len(edges))]
            for _ in range(5):
                next_frontier = []
                for marking, counts in frontier:
                    terminal = modes_index[tuple(marking[p] for p in controls)]
                    values = {('final', p): n for p, n in enumerate(marking)}
                    values.update({('count', e): n for e, n in enumerate(counts)})
                    rows = list(master_rows(problem, controls, modes, edges, terminal))
                    for place in range(3):
                        for flags in itertools.product((False, True), repeat=len(modes)):
                            cut = dict(place=place, modes=[q for q, flag in enumerate(flags) if flag])
                            rows.append(cut_row(problem, controls, modes, edges, terminal, finite, cut))
                    for terms, rhs in rows:
                        self.assertGreaterEqual(sum(values[k] * a for k, a in terms), rhs)
                    for t, transition in enumerate(problem['transitions']):
                        if any(marking[p] < n for p, n in transition['pre']):
                            continue
                        successor = marking.copy()
                        for p, n in transition['pre']:
                            successor[p] -= n
                        for p, n in transition['post']:
                            successor[p] += n
                        target = modes_index[tuple(successor[p] for p in controls)]
                        used = counts.copy()
                        used[edges_index[terminal, target, t]] += 1
                        next_frontier.append((successor, used))
                frontier = next_frontier

    def test_rejects_malformed_and_unsound_certificates(self):
        problem, proof = negative()
        changes = [
            lambda p: p['terminals'].pop(),
            lambda p: p.update(controls=[False]),
            lambda p: p.update(controls=[0, 0]),
            lambda p: p.update(extra=1),
            lambda p: p['bounds']['potentials'].clear(),
            lambda p: p['bounds']['potentials'][0]['weights'][0].__setitem__(1, '-1'),
            lambda p: p['terminals'][0].update(multipliers=[[2, '-1'], [4, '1']]),
            lambda p: p['terminals'][0].update(multipliers=[[2, '0'], [4, '1']]),
            lambda p: p['terminals'][0].update(multipliers=[[2, '1'], [2, '1']]),
            lambda p: p['terminals'][0].update(multipliers=[[4, '1']]),
            lambda p: p['terminals'][0].update(cuts=[dict(place=0, modes=[3])]),
            lambda p: p['terminals'][0].update(cuts=[dict(place=0, modes=[0, 0])]),
        ]
        for change in changes:
            changed = copy.deepcopy(proof)
            change(changed)
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                verify_finite_token_cut(problem, changed)
        reachable = copy.deepcopy(problem)
        reachable['target'][0]['bound'] = 2
        with self.assertRaises(ValueError):
            verify_finite_token_cut(reachable, proof)
        increasing = copy.deepcopy(problem)
        increasing['transitions'][0]['post'] = [[0, 2]]
        with self.assertRaises(ValueError):
            verify_finite_token_cut(increasing, proof)

    def test_rejects_invalid_problem_and_incomplete_graphs(self):
        problem = fixture()
        problem['initial'][0] = True
        with self.assertRaises(ValueError):
            validate_problem(problem)
        problem = fixture()
        problem['transitions'][0]['pre'].append([0, 1])
        with self.assertRaises(ValueError):
            validate_problem(problem)
        problem = dict(places=['x'], initial=[4096], transitions=[
            dict(name='consume', pre=[[0, 1]], post=[])], target=[])
        with self.assertRaisesRegex(ValueError, 'mode limit'):
            reconstruct(problem, [0], [4096])
        problem['transitions'] = [dict(name=str(i), pre=[], post=[]) for i in range(8193)]
        with self.assertRaisesRegex(ValueError, 'edge limit'):
            reconstruct(problem, [], [4096])


if __name__ == '__main__':
    unittest.main()
