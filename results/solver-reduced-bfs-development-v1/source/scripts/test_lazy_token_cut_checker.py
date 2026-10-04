import copy
from fractions import Fraction
import itertools
import unittest

from finite_token_cut_checker import checked_bounds, cut_row, master_rows, reconstruct
from lazy_token_cut_checker import (
    Work, edge_coefficient, reconstruct_modes, verify_lazy_token_cut,
)
from test_finite_token_cut_checker import bounds, fixture, negative


class LazyCheckerTests(unittest.TestCase):
    def test_existing_negative_and_dispatch(self):
        problem, proof = negative()
        proof['kind'] = 'lazy-finite-token-cut-v1'
        self.assertEqual(verify_lazy_token_cut(problem, proof), 'python-lazy-finite-token-cut')
        from benchmark import verify
        self.assertEqual(verify(problem, dict(verdict='unreachable', proof=proof)),
                         'python-lazy-finite-token-cut')

    def test_omitted_producing_stutter_invalidates_restricted_refutation(self):
        problem = dict(places=['x'], initial=[0], transitions=[
            dict(name='produce', pre=[], post=[[0, 1]])
        ], target=[dict(coefficients=[1], bound=1, equality=False)])
        proof = dict(kind='lazy-finite-token-cut-v1', controls=[],
                     bounds=dict(kind='place-bounds-v1', potentials=[]),
                     terminals=[dict(cuts=[], multipliers=[[0, '1'], [2, '1']])])
        with self.assertRaisesRegex(ValueError, 'original edge invalidates'):
            verify_lazy_token_cut(problem, proof)
        problem['transitions'][0]['post'] = []
        self.assertEqual(verify_lazy_token_cut(problem, proof), 'python-lazy-finite-token-cut')

    def test_stutters_do_not_consume_nonstutter_cap(self):
        problem = dict(places=['x'], initial=[0], transitions=[
            dict(name=str(i), pre=[], post=[]) for i in range(8200)
        ], target=[dict(coefficients=[1], bound=1, equality=False)])
        proof = dict(kind='lazy-finite-token-cut-v1', controls=[],
                     bounds=dict(kind='place-bounds-v1', potentials=[]),
                     terminals=[dict(cuts=[], multipliers=[[0, '1'], [2, '1']])])
        self.assertEqual(verify_lazy_token_cut(problem, proof), 'python-lazy-finite-token-cut')
        with self.assertRaisesRegex(ValueError, 'edge limit'):
            reconstruct(problem, [], [None])

    def test_modes_match_explicit_weighted_projection_for_every_subset(self):
        problem = fixture()
        finite = checked_bounds(problem, bounds())
        for flags in itertools.product((False, True), repeat=3):
            controls = [i for i, included in enumerate(flags) if included]
            expected, _ = reconstruct(problem, controls, finite)
            modes, indices, _ = reconstruct_modes(problem, controls, finite, Work())
            self.assertEqual(modes, expected)
            self.assertEqual(indices, {mode: i for i, mode in enumerate(modes)})

    def test_streaming_columns_match_full_matrix(self):
        problem = fixture()
        problem['target'] = [dict(coefficients=[1, -1, 0], bound=1, equality=True)]
        finite = checked_bounds(problem, bounds())
        for controls in ([], [0], [0, 1], [0, 2]):
            modes, edges = reconstruct(problem, controls, finite)
            for terminal in range(len(modes)):
                for p in range(3):
                    for flags in itertools.product((False, True), repeat=len(modes)):
                        cuts = [dict(place=p, modes=[i for i, flag in enumerate(flags) if flag])]
                        rows = list(master_rows(problem, controls, modes, edges, terminal))
                        cut_offset = len(rows)
                        mode_offset = cut_offset - 2*len(modes)
                        rows.append(cut_row(problem, controls, modes, edges, terminal, finite, cuts[0]))
                        weights = [Fraction((i*7) % 11, 13) for i in range(len(rows))]
                        for edge, (source, target, tr) in enumerate(edges):
                            expected = sum(weight * sum(a for key, a in terms if key == ('count', edge))
                                           for weight, (terms, _) in zip(weights, rows))
                            observed = edge_coefficient(problem, controls, modes, finite, source, target,
                                                        tr, cuts, weights, mode_offset, cut_offset, Work())
                            self.assertEqual(observed, expected)

    def test_unbounded_crossing_rejected_even_with_zero_cut_multiplier(self):
        problem = fixture()
        finite = [2, 2, None]
        modes, edges = reconstruct(problem, [0], finite)
        rows = list(master_rows(problem, [0], modes, edges, 0))
        cut_offset = len(rows)
        weights = [Fraction(0)] * (cut_offset + 1)
        with self.assertRaisesRegex(ValueError, 'unbounded outgoing'):
            edge_coefficient(problem, [0], modes, finite, 0, 1, 0,
                             [dict(place=2, modes=[0])], weights,
                             cut_offset - 2*len(modes), cut_offset, Work())

    def test_rejects_malformed_incomplete_and_resource_limited_proofs(self):
        problem, proof = negative()
        proof['kind'] = 'lazy-finite-token-cut-v1'
        mutations = []
        for key, value in [('controls', [0, 0]), ('terminals', proof['terminals'][:-1]),
                           ('kind', 'finite-token-cut-v1')]:
            changed = copy.deepcopy(proof)
            changed[key] = value
            mutations.append(changed)
        changed = copy.deepcopy(proof)
        changed['terminals'][0]['multipliers'][0][1] = '-1'
        mutations.append(changed)
        changed = copy.deepcopy(proof)
        changed['active_edges'] = []
        mutations.append(changed)
        for changed in mutations:
            with self.assertRaises(ValueError):
                verify_lazy_token_cut(problem, changed)
        with self.assertRaisesRegex(ValueError, 'work limit'):
            verify_lazy_token_cut(problem, proof, max_work=0)


if __name__ == '__main__':
    unittest.main()
