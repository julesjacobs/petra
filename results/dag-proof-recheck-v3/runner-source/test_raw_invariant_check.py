import copy
import time
import unittest
from unittest.mock import patch

from raw_invariant_check import verify
from raw_stress_worker import U64_MAX


def fixture():
    q = dict(format="ser-raw-v1", places=["ready", "pending", "response"], initial=[1, 0, 0],
             transitions=[dict(name="start", pre=[[0, 1]], post=[[1, 1]]),
                          dict(name="flush", pre=[[1, 1]], post=[[0, 1], [2, 2]])],
             target=dict(kind="completed-outside-semilinear", zero_places=[1], response_places=[2],
                         excluded_semilinear=[dict(base=[], periods=[[[2, 2]]])]))
    cert = dict(format="raw-component-invariant-v1", control_places=[0, 1],
                credits=[dict(place=1, terms=[[2, 2]])], initial_node=0, initial_coefficients=[],
                nodes=[dict(control=[1, 0], component=0,
                            edges=[dict(transition=0, target=1, base_coefficients=[[0, 1]],
                                        period_coefficients=[[[0, 1]]])]),
                       dict(control=[0, 1], component=0,
                            edges=[dict(transition=1, target=0, base_coefficients=[],
                                        period_coefficients=[[[0, 1]]])])])
    return q, cert


class RawInvariantTests(unittest.TestCase):
    def check(self, q, cert, **kwargs):
        return verify(q, cert, time.monotonic() + 3, **kwargs)

    def test_credit_controller_certificate(self):
        self.assertEqual(self.check(*fixture()), "python-raw-component-invariant")

    def test_missing_duplicate_and_extra_edges(self):
        q, cert = fixture()
        for change in ("missing", "duplicate", "disabled"):
            bad = copy.deepcopy(cert)
            if change == "missing":
                bad["nodes"][0]["edges"] = []
            elif change == "duplicate":
                bad["nodes"][0]["edges"] *= 2
            else:
                bad["nodes"][0]["edges"].append(copy.deepcopy(cert["nodes"][1]["edges"][0]))
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.check(q, bad)

    def test_affine_base_period_and_destination_forgery(self):
        q, cert = fixture()
        for field, value in [("base_coefficients", []), ("period_coefficients", [[]]),
                             ("period_coefficients", []), ("target", 0)]:
            bad = copy.deepcopy(cert)
            bad["nodes"][0]["edges"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.check(q, bad)

    def test_sparse_coefficients_reject_bool_zero_overflow_and_repetition(self):
        q, cert = fixture()
        for value in ([[True, 1]], [[0, True]], [[0, 0]], [[0, -1]], [[0, U64_MAX + 1]],
                      [[1, 1]], [[0, 1], [0, 1]], [1], [[0, 1, 2]]):
            bad = copy.deepcopy(cert)
            bad["nodes"][0]["edges"][0]["base_coefficients"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.check(q, bad)

    def test_credits_restricted_to_completion_zero_and_response_columns(self):
        q, cert = fixture()
        for credits in ([], [dict(place=0, terms=[[2, 2]])], [dict(place=2, terms=[[2, 2]])],
                        cert["credits"] * 2, [dict(place=1, terms=[[0, 2]])],
                        [dict(place=1, terms=[[2, 1], [2, 1]])],
                        [dict(place=1, terms=[[2, 0]])], [dict(place=1, terms=[[2, True]])]):
            bad = copy.deepcopy(cert); bad["credits"] = credits
            with self.subTest(credits=credits), self.assertRaises(ValueError):
                self.check(q, bad)

    def test_initial_membership_and_controller_forgery(self):
        q, cert = fixture()
        for field, value in [("initial_node", 1), ("initial_node", True),
                             ("initial_coefficients", [[0, 1]])]:
            bad = copy.deepcopy(cert); bad[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.check(q, bad)

    def test_self_loop_with_nonzero_credited_effect_needs_edge(self):
        q, cert = fixture()
        q["transitions"].append(dict(name="repeat", pre=[[0, 1]], post=[[0, 1], [2, 2]]))
        with self.assertRaisesRegex(ValueError, "missing"):
            self.check(q, cert)
        cert["nodes"][0]["edges"].append(dict(transition=2, target=0, base_coefficients=[[0, 1]],
                                             period_coefficients=[[[0, 1]]]))
        self.check(q, cert)

    def test_index_checks_full_weighted_preset_and_rejects_skipped_edges(self):
        for preset in ([[0, 2]], [[0, 1], [1, 1]]):
            q, cert = fixture()
            q["transitions"].append(dict(name="disabled", pre=preset,
                                         post=preset + [[2, 2]]))
            self.check(q, cert)
            cert["nodes"][0]["edges"].append(dict(
                transition=2, target=0, base_coefficients=[[0, 1]],
                period_coefficients=[[[0, 1]]]))
            with self.subTest(preset=preset), self.assertRaises(ValueError):
                self.check(q, cert)

    def test_unselected_guard_cannot_hide_an_obligation(self):
        q, cert = fixture()
        q["transitions"].append(dict(name="unselected", pre=[[2, 100]], post=[[2, 102]]))
        with self.assertRaisesRegex(ValueError, "missing"):
            self.check(q, cert)
        for i, node in enumerate(cert["nodes"]):
            node["edges"].append(dict(transition=2, target=i, base_coefficients=[[0, 1]],
                                      period_coefficients=[[[0, 1]]]))
        self.check(q, cert)

    def test_globally_stuttering_transition_is_omitted(self):
        q, cert = fixture()
        q["transitions"].append(dict(name="read", pre=[[2, 1]], post=[[2, 1]]))
        self.check(q, cert)
        cert["nodes"][0]["edges"].append(dict(transition=2, target=0, base_coefficients=[],
                                             period_coefficients=[[[0, 1]]]))
        with self.assertRaisesRegex(ValueError, "extra"):
            self.check(q, cert)

    def test_empty_periods_and_empty_controller(self):
        q, cert = fixture()
        q["transitions"] = []
        q["target"]["excluded_semilinear"][0]["periods"] = []
        cert.update(control_places=[], nodes=[dict(control=[], component=0, edges=[])])
        self.check(q, cert)
        cert["initial_coefficients"] = [[0, 1]]
        with self.assertRaises(ValueError):
            self.check(q, cert)

    def test_nonidentity_period_map_between_original_components(self):
        q, cert = fixture()
        q["transitions"] = q["transitions"][:1]
        q["target"]["excluded_semilinear"].append(dict(base=[], periods=[[[2, 1]]]))
        cert["credits"] = []
        cert["nodes"][1].update(component=1, edges=[])
        cert["nodes"][0]["edges"][0].update(base_coefficients=[], period_coefficients=[[[0, 2]]])
        self.check(q, cert)
        cert["nodes"][0]["edges"][0]["period_coefficients"] = [[[0, 1]]]
        with self.assertRaisesRegex(ValueError, "period mapping"):
            self.check(q, cert)

    def test_sparse_coefficients_must_be_sorted(self):
        q, cert = fixture()
        q["transitions"] = []
        q["initial"][2] = 4
        q["target"]["excluded_semilinear"][0]["periods"] *= 2
        cert["nodes"] = [dict(control=[1, 0], component=0, edges=[])]
        cert["initial_coefficients"] = [[0, 1], [1, 1]]
        self.check(q, cert)
        cert["initial_coefficients"].reverse()
        with self.assertRaisesRegex(ValueError, "sorted"):
            self.check(q, cert)

    def test_exact_intermediate_arithmetic_exceeds_u64(self):
        q, cert = fixture()
        q["initial"] = [0, U64_MAX, 0]
        q["transitions"] = []
        q["target"]["excluded_semilinear"][0]["periods"] = [[[2, U64_MAX]]]
        cert.update(control_places=[], initial_coefficients=[[0, U64_MAX]],
                    credits=[dict(place=1, terms=[[2, U64_MAX]])],
                    nodes=[dict(control=[], component=0, edges=[])])
        self.check(q, cert)

    def test_projected_control_overflow_rejected(self):
        q, cert = fixture()
        q["initial"] = [U64_MAX, 0, 0]
        q["transitions"] = [dict(name="grow", pre=[], post=[[0, 1]])]
        cert["nodes"] = [dict(control=[U64_MAX, 0], component=0,
                              edges=[dict(transition=0, target=0, base_coefficients=[],
                                          period_coefficients=[[[0, 1]]])])]
        with self.assertRaisesRegex(ValueError, "overflow"):
            self.check(q, cert)

    def test_control_and_node_schema(self):
        q, cert = fixture()
        for selected in ([1, 0], [0, 0], [True, 1], [0, 3]):
            bad = copy.deepcopy(cert); bad["control_places"] = selected
            with self.assertRaises(ValueError):
                self.check(q, bad)
        for field, value in [("control", [True, 0]), ("control", [1]), ("component", True),
                             ("component", 1)]:
            bad = copy.deepcopy(cert); bad["nodes"][0][field] = value
            with self.assertRaises(ValueError):
                self.check(q, bad)
        cert["nodes"].append(copy.deepcopy(cert["nodes"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.check(q, cert)

    def test_original_query_validation_and_unknown_format(self):
        q, cert = fixture()
        q["initial"][0] = True
        with self.assertRaises(ValueError):
            self.check(q, cert)
        q, cert = fixture(); cert["format"] = "unknown"
        with self.assertRaises(ValueError):
            self.check(q, cert)
        with self.assertRaises(ValueError):
            self.check({}, cert)

    def test_limits_never_accept_partial_verification(self):
        q, cert = fixture()
        for limit in (0, 30):
            with self.assertRaises(TimeoutError):
                self.check(q, cert, max_obligations=limit)
        with self.assertRaises(TimeoutError):
            verify(q, cert, time.monotonic() - 1)
        with patch("raw_invariant_check.time.monotonic", side_effect=[0] * 40 + [2] * 1000):
            with self.assertRaises(TimeoutError):
                verify(q, cert, 1)
        with self.assertRaises(ValueError):
            self.check(q, cert, max_obligations=True)


if __name__ == "__main__":
    unittest.main()
