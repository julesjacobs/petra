"""Run with: vendor/venv/bin/python tests/check_signed_threshold.py"""

import copy
import itertools
import pathlib
import random
import sys
import time
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from signed_threshold_checker import _unsatisfiable, verify_signed_threshold


def problem(initial, transitions=(), target=()):
    return {"places": [f"p{i}" for i in range(len(initial))],
            "initial": list(initial), "transitions": list(transitions), "target": list(target)}


def transition(pre=(), post=()):
    return {"name": "t", "pre": [list(arc) for arc in pre],
            "post": [list(arc) for arc in post]}


def row(coefficients, bound, equality=False):
    return {"coefficients": coefficients, "bound": bound, "equality": equality}


def literal(form, threshold, negated=False):
    return {"form": form, "threshold": str(threshold), "negated": negated}


def proof(forms, clauses):
    return {"kind": "signed-threshold-invariant-v1", "forms": forms, "clauses": clauses}


class SignedThresholdCheckerTests(unittest.TestCase):
    def check(self, p, certificate):
        self.assertEqual(verify_signed_threshold(p, certificate),
                         "python-signed-threshold-invariant")

    def reject(self, p, certificate):
        with self.assertRaises(ValueError):
            verify_signed_threshold(p, certificate)

    def test_weighted_unbounded_net(self):
        p = problem([2, 0], [transition([(0, 2)], [(0, 2), (1, 3)])],
                    [row([1, 0], 3)])
        cert = proof([[[0, "1"]]], [[literal(0, 3, True)]])
        self.check(p, cert)
        p["transitions"][0]["post"][0][1] = 3
        self.reject(p, cert)

    def test_signed_lower_bound(self):
        p = problem([3], [transition(post=[(0, 2)])], [row([-1], -2)])
        self.check(p, proof([[[0, "-1"]]], [[literal(0, -2, True)]]))

    def test_equality_zero_target(self):
        p = problem([1], [transition(post=[(0, 1)])], [row([1], 0, True)])
        cert = proof([[[0, "1"]]], [[literal(0, 1)]])
        self.check(p, cert)
        p["target"][0]["equality"] = False
        self.reject(p, cert)

    def test_read_guard_is_used(self):
        p = problem([0, 0], [transition([(0, 2)], [(0, 2), (1, 1)])],
                    [row([0, 1], 1)])
        cert = proof([[[0, "1"]], [[1, "1"]]],
                     [[literal(0, 2, True)], [literal(1, 1, True)]])
        self.check(p, cert)
        p["transitions"][0] = transition(post=[(1, 1)])
        self.reject(p, cert)

    def test_signed_affine_form(self):
        p = problem([0, 0], [transition(post=[(0, 2), (1, 1)])],
                    [row([1, -1], -1, True)])
        cert = proof([[[0, "1"], [1, "-1"]]], [[literal(0, 0)]])
        self.check(p, cert)
        p["transitions"][0] = transition(post=[(1, 1)])
        self.reject(p, cert)

    def test_duplicate_numeric_forms_and_threshold_order(self):
        p = problem([1], target=[row([1], 3)])
        cert = proof([[[0, "+01"]], [[0, "1"]]],
                     [[literal(0, 2, True)], [literal(1, 1)]])
        self.check(p, cert)
        p["initial"] = [2]
        self.reject(p, cert)

    def test_binary_clause_and_original_conjunction(self):
        p = problem([1, 0], [transition([(0, 1)], [(1, 1)]),
                             transition([(1, 1)], [(0, 1)])],
                    [row([1, 0], 1), row([0, 1], 1)])
        cert = proof([[[0, "1"]], [[1, "1"]]],
                     [[literal(0, 1, True), literal(1, 1, True)],
                      [literal(0, 2, True)], [literal(1, 2, True)]])
        self.check(p, cert)
        p["target"].pop()
        self.reject(p, cert)

    def test_empty_invariant_and_universal_sign_facts(self):
        empty = proof([], [])
        self.check(problem([0], target=[row([-1], 1)]), empty)
        self.check(problem([0], target=[row([1], -1, True)]), empty)
        self.check(problem([], target=[row([], 1)]), empty)
        self.check(problem([], target=[row([], -1, True)]), empty)
        self.reject(problem([], target=[]), empty)
        self.reject(problem([], target=[row([], 0, True)]), empty)
        self.reject(problem([0], target=[row([1], 0)]), empty)

    def test_numeric_extrema_and_large_pullbacks(self):
        maximum = 2**64 - 1
        minimum = -(2**63)
        p = problem([maximum], [transition([(0, maximum)], [(0, maximum)])],
                    [row([minimum], 2**63 - 1, True)])
        cert = proof([[[0, str(minimum)]]], [[literal(0, minimum * maximum)]])
        self.check(p, cert)
        p = problem([maximum], [transition(post=[(0, maximum)])],
                    [row([1], 0, True)])
        self.check(p, proof([[[0, "1"]]], [[literal(0, maximum)]]))
        huge = "1" + "0" * 5000
        self.check(problem([1], target=[row([-1], 1)]),
                   proof([[[0, huge]]], [[literal(0, huge)]]))

    def test_validate_every_original_target_row(self):
        p = problem([0], target=[row([-1], 1), row([], 0)])
        self.reject(p, proof([], []))

    def test_malformed_problem_schema(self):
        base = problem([0], [transition()], [row([-1], 1)])
        mutations = [
            lambda p: p.update(places=[1]),
            lambda p: p.update(initial=[True]),
            lambda p: p.update(initial=[-1]),
            lambda p: p.update(initial=[2**64]),
            lambda p: p["transitions"][0].update(name=1),
            lambda p: p["transitions"][0].update(pre=[[0, 0]]),
            lambda p: p["transitions"][0].update(pre=[[0, True]]),
            lambda p: p["transitions"][0].update(post=[[0, 2**64]]),
            lambda p: p["transitions"][0].update(pre=[[1, 1]]),
            lambda p: p["transitions"][0].update(pre=[[0, 1], [0, 1]]),
            lambda p: p["target"][0].update(coefficients=[True]),
            lambda p: p["target"][0].update(coefficients=[-(2**63) - 1]),
            lambda p: p["target"][0].update(bound=2**63),
            lambda p: p["target"][0].update(equality=1),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutations.index(mutation)):
                p = copy.deepcopy(base)
                mutation(p)
                self.reject(p, proof([], []))

    def test_malformed_proof(self):
        p = problem([0], target=[row([-1], 1)])
        cert = proof([[[0, "1"]]], [[literal(0, 0)]])
        mutations = [
            lambda c: c.update(extra=[]),
            lambda c: c.update(kind="wrong"),
            lambda c: c.update(forms=[[[0, "0"]]]),
            lambda c: c.update(forms=[[[0, "1"], [0, "2"]]]),
            lambda c: c.update(forms=[[[True, "1"]]]),
            lambda c: c.update(forms=[[[1, "1"]]]),
            lambda c: c.update(forms=[[[0, 1]]]),
            lambda c: c.update(clauses=[[]]),
            lambda c: c.update(clauses=[[literal(0, 0)] * 3]),
            lambda c: c["clauses"][0][0].update(form=True),
            lambda c: c["clauses"][0][0].update(negated=0),
            lambda c: c["clauses"][0][0].update(extra=0),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutations.index(mutation)):
                changed = copy.deepcopy(cert)
                mutation(changed)
                self.reject(p, changed)
        for value in ("", "+", "-", " 1", "1 ", "1_0", "١", "1.0", "--1"):
            changed = copy.deepcopy(cert)
            changed["clauses"][0][0]["threshold"] = value
            self.reject(p, changed)

    def test_deadline(self):
        with self.assertRaisesRegex(TimeoutError, "deadline"):
            verify_signed_threshold(problem([], target=[row([], 1)]), proof([], []),
                                    deadline=time.monotonic() - 1)

    def test_boolean_kernel_against_exhaustive_valuations(self):
        rng = random.Random(12783)
        forms = [(), ((0, 1),), ((0, -1),), ((0, 1), (1, -1))]
        for _ in range(400):
            candidates = [(rng.choice(forms), rng.randrange(-1, 3)) for _ in range(5)]
            clauses = [[(*rng.choice(candidates), bool(rng.randrange(2)))
                        for _ in range(rng.randrange(1, 3))] for _ in range(rng.randrange(8))]
            atoms = list({(f, k) for c in clauses for f, k, _ in c})
            satisfiable = False
            for values in itertools.product((False, True), repeat=len(atoms)):
                valuation = dict(zip(atoms, values))
                legal = True
                for (form, k), value in valuation.items():
                    if (k <= 0 and all(a >= 0 for _, a in form) and not value or
                            k > 0 and all(a <= 0 for _, a in form) and value):
                        legal = False
                    for (other_form, other_k), other_value in valuation.items():
                        if form == other_form and k >= other_k and value and not other_value:
                            legal = False
                if legal and all(any(valuation[(f, k)] != neg for f, k, neg in c)
                                 for c in clauses):
                    satisfiable = True
                    break
            self.assertEqual(_unsatisfiable(clauses, lambda: None), not satisfiable)

    def test_finite_net_exhaustive_invariant_checks(self):
        transitions = [transition([(0, 1)], [(1, 1)]),
                       transition([(1, 1)], [(0, 1)])]
        forms = [[[0, "1"]], [[1, "1"]]]
        literals = [literal(f, k, neg) for f in range(2) for k in range(3)
                    for neg in (False, True)]
        reachable = [(2, 0), (1, 1), (0, 2)]
        base = [[literal(0, 3, True)], [literal(1, 3, True)],
                [literal(0, 1, True), literal(1, 2, True)],
                [literal(0, 2, True), literal(1, 1, True)]]
        accepted = 0
        for left, right in itertools.combinations_with_replacement(literals, 2):
            cert = proof(forms, base + [[left, right]])
            for target_place, target_bound in itertools.product(range(2), range(4)):
                coefficients = [int(i == target_place) for i in range(2)]
                p = problem([2, 0], transitions, [row(coefficients, target_bound)])
                try:
                    verify_signed_threshold(p, cert)
                except ValueError:
                    continue
                accepted += 1
                for marking in reachable:
                    self.assertTrue(any((marking[l["form"]] >= int(l["threshold"]))
                                        != l["negated"] for l in (left, right)))
                    self.assertLess(marking[target_place], target_bound)
        self.assertGreater(accepted, 0)


if __name__ == "__main__":
    unittest.main()
