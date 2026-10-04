import copy
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest import mock

import benchmark_stress_raw as benchmark
import raw_stress_worker as worker
from process_runner import run


def query():
    return dict(format="ser-raw-v1", places=["r", "pending"], initial=[0, 1],
                transitions=[dict(name="return", pre=[[1, 1]], post=[[0, 1]])],
                target=dict(kind="completed-outside-semilinear", zero_places=[1], response_places=[0],
                            excluded_semilinear=[dict(base=[], periods=[[[0, 2]]])]))


class PipelineTests(unittest.TestCase):
    def test_schema_rejects_invalid_dimensions_arcs_and_semilinear_coordinates(self):
        bad = []
        q = query(); q["initial"] = [0]; bad.append(q)
        q = query(); q["initial"][1] = True; bad.append(q)
        q = query(); q["transitions"][0]["pre"].append([1, 1]); bad.append(q)
        q = query(); q["target"]["zero_places"] = [0]; bad.append(q)
        q = query(); q["target"]["excluded_semilinear"][0]["periods"] = [[[1, 2]]]; bad.append(q)
        q = query(); q["transitions"][0]["post"] = [[0, 2**64]]; bad.append(q)
        for q in bad:
            with self.subTest(q=q), self.assertRaises(ValueError):
                worker.validate(q)
        worker.validate(query())

    def test_duplicate_json_fields_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "query.json"
            path.write_text('{"format":"ser-raw-v1","format":"other"}')
            with self.assertRaises(ValueError):
                worker.load_json(path)
            path.write_text('{"unused":NaN}')
            with self.assertRaisesRegex(ValueError, "JSON constant"):
                worker.load_json(path)

    def test_false_witness_rejected_before_z3(self):
        q = query()
        for answer in [dict(verdict="reachable", trace=[0, 0], marking=[2, 0]),
                       dict(verdict="reachable", trace=[0], marking=[0, 0]),
                       dict(verdict="reachable", trace=[], marking=[0, 1]),
                       dict(verdict="reachable", trace=[True], marking=[1, 0])]:
            with self.subTest(answer=answer), self.assertRaises(ValueError):
                worker.verify_positive(q, answer, time.monotonic() + 1)

    def test_unknown_z3_is_never_nonmembership(self):
        class Solver:
            def set(self, **kwargs): pass
            def add(self, *args): pass
            def check(self): return "unknown"
            def reason_unknown(self): return "synthetic resource limit"
        class UnknownZ3:
            unknown, unsat = "unknown", "unsat"
            @staticmethod
            def Int(name): return 0
        UnknownZ3.Solver = Solver
        with self.assertRaisesRegex(worker.VerificationUnknown, "Z3 returned unknown"):
            worker.verify_positive(query(), dict(verdict="reachable", trace=[0], marking=[1, 0]),
                                   time.monotonic() + 1, UnknownZ3)

    def test_positive_and_serial_member_use_independent_z3(self):
        import z3
        q = query()
        answer = dict(verdict="reachable", trace=[0], marking=[1, 0])
        self.assertEqual(worker.verify_positive(q, answer, time.monotonic() + 2, z3),
                         "python-original-replay-z3-nonmembership")
        q["target"]["excluded_semilinear"][0] = dict(base=[[0, 1]], periods=[])
        with self.assertRaisesRegex(ValueError, "belongs to serial"):
            worker.verify_positive(q, answer, time.monotonic() + 2, z3)

    def test_sparse_membership_formula_matches_dense_z3(self):
        import random
        import z3
        rng = random.Random(20260928)
        for case in range(64):
            n = 1 + case % 5
            vector = lambda: [[i, w] for i in range(n) if (w := rng.randrange(3))]
            base = vector()
            periods = [vector() for _ in range(case % 6)]
            if case % 2:
                marking = [dict(base).get(i, 0) for i in range(n)]
                for period in periods:
                    coefficient = rng.randrange(3)
                    for i, w in period:
                        marking[i] += coefficient * w
            else:
                marking = [rng.randrange(6) for _ in range(n)]
            ns = [z3.Int(f"old_{i}") for i in range(len(periods))]
            dense = z3.Solver()
            dense.add(*[k >= 0 for k in ns])
            dense.add(*[marking[i] == dict(base).get(i, 0)
                        + sum(k * dict(v).get(i, 0) for k, v in zip(ns, periods))
                        for i in range(n)])
            expected = dense.check()
            self.assertIn(expected, [z3.sat, z3.unsat])
            q = dict(format="ser-raw-v1", places=[str(i) for i in range(n)],
                     initial=marking, transitions=[], target=dict(
                         kind="completed-outside-semilinear", zero_places=[],
                         response_places=list(range(n)),
                         excluded_semilinear=[dict(base=base, periods=periods)]))
            worker.validate(q)
            answer = dict(verdict="reachable", trace=[], marking=marking)
            with self.subTest(case=case):
                if expected == z3.sat:
                    with self.assertRaisesRegex(ValueError, "belongs to serial"):
                        worker.verify_positive(q, answer, time.monotonic() + 2, z3)
                else:
                    self.assertEqual(worker.verify_positive(q, answer, time.monotonic() + 2, z3),
                                     "python-original-replay-z3-nonmembership")

    def make_collection(self, root):
        cases = [dict(name=name, source=name + ".ser", sha256="source-" + name, role="new-scaling-case",
                      exact_source_overlaps=[], source_expectation=dict(serializable=False))
                 for name in ["exported", "failed", "unattempted"]]
        for case in cases[:2]:
            directory = root / case["name"]; directory.mkdir()
            path = directory / case["source"]
            path.write_text("request example { 0 }\n")
            case["sha256"] = benchmark.sha256(path)
        manifest_path = root / "source-manifest.json"
        manifest_path.write_text(json.dumps(dict(format="ser-stress-sources-v1", cases=cases)))
        path = root / "query.json"
        path.write_text(json.dumps(query()))
        collection = dict(format="ser-stress-collection-v1", source_manifest_sha256=benchmark.sha256(manifest_path),
                          attempts=[dict(name="exported", source_sha256=cases[0]["sha256"], status="exported-unvalidated",
                                         query="query.json", artifacts=[dict(path="query.json", sha256=benchmark.sha256(path))]),
                                    dict(name="failed", source_sha256=cases[1]["sha256"], status="memory-limit")])
        (root / "collection.json").write_text(json.dumps(collection))

    def test_failed_exports_and_unattempted_sources_remain_in_denominator(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.make_collection(root)
            selected = benchmark.select_sources(root)
            self.assertEqual(len(selected), 3)
            self.assertEqual([s["export_status"] for s in selected],
                             ["exported-unvalidated", "memory-limit", "not-collected"])
            self.assertEqual(sum(s["availability"] == "export-unavailable" for s in selected), 2)
            report = benchmark.report_text(selected, [dict(query="exported", method="raw-bfs", verdict="reachable")],
                                           ["raw-bfs"], 1, 1)
            self.assertIn("| raw-bfs | 3 | 1 | 0 | 0 | 2 |", report)

    def test_changed_input_hash_prevents_benchmarking(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.make_collection(root)
            selected = benchmark.select_sources(root)
            (root / "query.json").write_text("{}")
            output = root / "result"; output.mkdir()
            benchmark.freeze_inputs(selected, output)
            self.assertEqual(selected[0]["availability"], "input-hash-mismatch")
            self.assertNotIn("frozen_query", selected[0])

    def test_manifest_hash_change_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.make_collection(root)
            with (root / "source-manifest.json").open("a") as stream:
                stream.write("\n")
            with self.assertRaisesRegex(ValueError, "manifest hash"):
                benchmark.select_sources(root)

    def test_collection_selection_keeps_selected_unattempted_sources_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.make_collection(root)
            path = root / "collection.json"
            collection = json.loads(path.read_text())
            collection["selected_sources"] = ["exported", "unattempted"]
            path.write_text(json.dumps(collection))
            selected = benchmark.select_sources(root)
            self.assertEqual([s["name"] for s in selected], ["exported", "unattempted"])
            self.assertEqual(selected[1]["export_status"], "not-collected")
            self.assertEqual(len(benchmark.select_sources(root, all_sources=True)), 3)
            self.assertEqual([s["name"] for s in benchmark.select_sources(root, ["failed"])], ["failed"])

    def test_changed_source_bytes_prevent_benchmarking(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.make_collection(root)
            selected = benchmark.select_sources(root)
            (root / "exported/exported.ser").write_text("changed")
            output = root / "result"; output.mkdir()
            benchmark.freeze_inputs(selected, output)
            self.assertEqual(selected[0]["availability"], "source-hash-mismatch")
            self.assertTrue((output / "inputs/exported.ser").is_file())
            self.assertNotIn("frozen_query", selected[0])

    def test_exit_after_budget_and_final_rss_sample_never_accept_positive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "result.json").write_text(json.dumps(dict(verdict="reachable", status="verified-positive",
                                                             independent_check="python-original-replay-z3-nonmembership")))
            usage = dict(sampled_peak_rss_bytes=10, memory_limit_exceeded=False)
            result, expired, _ = benchmark.classify_bounded_worker(root, 0, False, usage, 1.001, 1, 20)
            self.assertTrue(expired)
            self.assertEqual(result["status"], "outer-timeout")
            result, expired, _ = benchmark.classify_bounded_worker(root, 0, False, usage, 0.5, 1, 5)
            self.assertTrue(expired)
            self.assertEqual(result["status"], "memory-limit")

    def test_raw_negative_remains_unsupported(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "query.json"; path.write_text(json.dumps(query()))
            args = SimpleNamespace(query=path, sha256=worker.sha256(path), directory=root, seconds=5,
                                   solver_fraction=0.8, method="raw-bfs", binary=Path("unused"), max_states=100)
            def fake_solver(command, stdout, **kwargs):
                stdout.write(json.dumps(dict(verdict="unreachable", proof={"kind": "unsupported"})))
                stdout.flush()
                return SimpleNamespace(returncode=0)
            with mock.patch.object(worker.subprocess, "run", side_effect=fake_solver):
                result = worker.execute(args)
            self.assertEqual(result["verdict"], "unknown")
            self.assertEqual(result["status"], "unsupported-negative")

    def negative_worker(self, q, proof):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "query.json"; path.write_text(json.dumps(q))
            args = SimpleNamespace(query=path, sha256=worker.sha256(path), directory=root, seconds=5,
                                   solver_fraction=0.8, method="raw-negative", binary=Path("unused"), max_states=100)
            def fake_solver(command, stdout, **kwargs):
                self.assertIn("raw-negative", command)
                stdout.write(json.dumps(dict(verdict="unreachable", proof=proof)))
                stdout.flush()
                return SimpleNamespace(returncode=0)
            with mock.patch.object(worker.subprocess, "run", side_effect=fake_solver):
                return worker.execute(args)

    def test_negative_worker_accepts_only_checked_original_proof(self):
        from test_raw_invariant_check import fixture
        q, proof = fixture()
        result = self.negative_worker(q, proof)
        self.assertEqual(result["verdict"], "unreachable", result)
        self.assertEqual(result["status"], "verified-negative")
        self.assertEqual(result["independent_check"], "python-raw-component-invariant")
        q["transitions"][1]["post"][-1][1] = 1
        result = self.negative_worker(q, proof)
        self.assertEqual(result["verdict"], "unknown")
        self.assertEqual(result["status"], "invalid-answer")
        self.assertEqual(result["stage"], "negative-verification")
        self.assertNotIn("independent_check", result)

    def test_negative_checker_exhaustion_preserves_unknown(self):
        from test_raw_invariant_check import fixture
        with mock.patch("raw_invariant_check.verify", side_effect=TimeoutError("work limit")):
            result = self.negative_worker(*fixture())
        self.assertEqual(result["verdict"], "unknown")
        self.assertEqual(result["status"], "verification-unknown")
        self.assertEqual(result["stage"], "negative-verification")
        self.assertNotIn("independent_check", result)

    def test_negative_worker_protocol_and_outer_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = dict(verdict="unreachable", status="verified-negative",
                          independent_check="python-raw-component-invariant")
            (root / "result.json").write_text(json.dumps(result))
            (root / "progress.json").write_text(json.dumps(dict(stage="negative-verification")))
            self.assertEqual(benchmark.classify_worker(root, 0, False, {})["verdict"], "unreachable")
            usage = dict(sampled_peak_rss_bytes=10, memory_limit_exceeded=False)
            for code, expired, wall, memory in [(0, True, 0.5, 20), (-9, False, 0.5, 20),
                                                (0, False, 1.1, 20), (0, False, 0.5, 5)]:
                checked, _, _ = benchmark.classify_bounded_worker(root, code, expired, usage, wall, 1, memory)
                self.assertEqual(checked["verdict"], "unknown")
            for key in ("status", "independent_check"):
                malformed = dict(result); malformed.pop(key)
                (root / "result.json").write_text(json.dumps(malformed))
                checked = benchmark.classify_worker(root, 0, False, {})
                self.assertEqual(checked["status"], "worker-protocol-error")

    def test_negative_harness_freezes_checker_and_runs_cli_worker(self):
        from test_raw_invariant_check import fixture
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.make_collection(root)
            q, proof = fixture()
            path = root / "query.json"; path.write_text(json.dumps(q))
            collection_path = root / "collection.json"
            collection = json.loads(collection_path.read_text())
            collection["attempts"][0]["artifacts"][0]["sha256"] = benchmark.sha256(path)
            collection_path.write_text(json.dumps(collection))
            fake = root / "solver"
            fake.write_text(f"#!{sys.executable}\nimport json\nprint(json.dumps({dict(verdict='unreachable', proof=proof)!r}))\n")
            fake.chmod(0o755)
            output = root / "results"
            argv = ["benchmark_stress_raw.py", "--corpus", str(root), "--output", str(output),
                    "--binary", str(fake), "--methods", "raw-negative", "--seconds", "4", "--memory-mib", "512"]
            with mock.patch.object(sys, "argv", argv), mock.patch.object(benchmark, "workspace_workloads", return_value=[]):
                benchmark.main()
            rows = [json.loads(line) for line in (output / "runs.jsonl").read_text().splitlines()]
            self.assertEqual(rows[0]["status"], "verified-negative", rows)
            self.assertEqual(rows[0]["independent_check"], "python-raw-component-invariant")
            environment = json.loads((output / "environment.json").read_text())
            self.assertEqual(environment["runner_sha256"]["raw_invariant_check.py"],
                             benchmark.sha256(output / "runner-source" / "raw_invariant_check.py"))
            self.assertIn("| raw-negative | 3 | 0 | 1 | 0 | 2 |", (output / "REPORT.md").read_text())
            report = benchmark.report_text([dict(availability="pending-validation", export_status="exported")],
                [dict(query="q", method="raw-negative", verdict="unreachable")], ["raw-negative"], 2, 4)
            self.assertIn("| raw-negative | 1 | 0 | 0 | 1 | 0 |", report)

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.make_collection(root)
            output = root / "existing"; output.mkdir()
            sentinel = output / "keep"; sentinel.write_text("previous evidence")
            binary = root / "binary"; binary.write_text("unused")
            argv = ["benchmark_stress_raw.py", "--corpus", str(root), "--output", str(output), "--binary", str(binary)]
            with mock.patch.object(sys, "argv", argv), mock.patch.object(benchmark, "workspace_workloads", return_value=[]):
                with self.assertRaises(FileExistsError):
                    benchmark.main()
            self.assertEqual(sentinel.read_text(), "previous evidence")

    def test_killed_worker_does_not_accept_partial_positive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "progress.json").write_text(json.dumps(dict(stage="positive-verification")))
            (root / "result.json").write_text(json.dumps(dict(verdict="reachable", status="verified-positive",
                                                              independent_check="python-original-replay-z3-nonmembership")))
            _, code, expired, usage = run([sys.executable, "-c", "import time; time.sleep(30)"],
                                         root, 0.1, root / "log")
            result = benchmark.classify_worker(root, code, expired, usage)
            self.assertTrue(expired)
            self.assertEqual(result["verdict"], "unknown")
            self.assertEqual(result["stage"], "positive-verification")

    def test_worker_end_to_end_and_input_inclusive_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "query.json"; path.write_text(json.dumps(query()))
            fake = root / "solver"
            fake.write_text(f"#!{sys.executable}\nimport json\nprint(json.dumps({dict(verdict='reachable', trace=[0], marking=[1, 0])!r}))\n")
            fake.chmod(0o755)
            directory = root / "run"; directory.mkdir()
            command = [sys.executable, str(Path(worker.__file__).resolve()), "--query", str(path),
                       "--sha256", worker.sha256(path), "--directory", str(directory), "--binary", str(fake),
                       "--raw-z3", str(fake), "--method", "raw-bfs", "--seconds", "4"]
            _, code, expired, usage = run(command, root, 4, root / "worker.log", memory_bytes=512 * 1024**2)
            result = benchmark.classify_worker(directory, code, expired, usage)
            self.assertEqual(result["verdict"], "reachable", result)
            path.write_text("{}")
            directory = root / "changed"; directory.mkdir()
            changed = copy.copy(command)
            changed[changed.index("--directory") + 1] = str(directory)
            _, code, expired, usage = run(changed, root, 4, root / "changed.log", memory_bytes=512 * 1024**2)
            result = benchmark.classify_worker(directory, code, expired, usage)
            self.assertEqual(result["status"], "input-invalid")
            self.assertFalse((directory / "solver.stdout").exists())


if __name__ == "__main__":
    unittest.main()
