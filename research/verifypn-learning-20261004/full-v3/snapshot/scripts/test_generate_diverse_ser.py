#!/usr/bin/env python3
"""Artifact integrity and finite-model checks; this is not a SER interpreter."""
import itertools
import json
from pathlib import Path
import tempfile
import unittest

import generate_diverse_ser as generator


class DiverseSources(unittest.TestCase):
    def test_manifest_hashes_and_unique_cases(self):
        files = generator.artifacts()
        self.assertEqual(files, generator.artifacts())
        manifest = json.loads(files["manifest.json"])
        self.assertEqual(manifest["format"], "ser-stress-sources-v1")
        self.assertEqual(len(manifest["cases"]), 12)
        self.assertEqual(len({case["name"] for case in manifest["cases"]}), 12)
        self.assertEqual(len({case["sha256"] for case in manifest["cases"]}), 12)
        self.assertEqual({case["family"] for case in manifest["cases"]},
                         {"ring-write-skew", "optimistic-aba-validation"})
        for case in manifest["cases"]:
            data = files[case["source"]]
            self.assertEqual(case["sha256"], generator.digest(data))
            self.assertEqual(case["bytes"], len(data))
            self.assertIsNone(case["solver_result"])
            self.assertFalse(case["source_expectation"]["mechanically_verified"])
        for line in files["SHA256SUMS"].decode().splitlines():
            sha, name = line.split("  ")
            self.assertEqual(sha, generator.digest(files[name]))

    def test_freeze_is_idempotent_and_refuses_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "sources"
            self.assertTrue(generator.freeze(output))
            self.assertFalse(generator.freeze(output))
            source = output / "write_skew_n3_racy.ser"
            source.write_text("changed")
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            with self.assertRaises(ValueError):
                generator.freeze(output)
            self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})

    def test_write_skew_schedule_has_no_serial_permutation(self):
        for sites in [3, 4, 5]:
            off = [0] * sites
            saved = [off[i] == 0 and off[(i + 1) % sites] == 0 for i in range(sites)]
            for i in range(sites):
                if saved[i]:
                    off[i] = 1
            self.assertTrue(all(saved))
            self.assertEqual(off, [1] * sites)
            for order in itertools.permutations(range(sites)):
                off = [0] * sites
                responses = []
                for i in order:
                    allowed = off[i] == 0 and off[(i + 1) % sites] == 0
                    responses.append(allowed)
                    if allowed:
                        off[i] = 1
                self.assertFalse(all(responses))

    def test_epoch_wrap_schedule_and_value_validation(self):
        for modulus in [3, 5, 9]:
            for initial_value in [0, 1]:
                for initial_epoch in range(modulus):
                    value, epoch = initial_value, initial_epoch
                    for _ in range(modulus):
                        value = 1 - value
                        epoch = (epoch + 1) % modulus
                    self.assertEqual(epoch, initial_epoch)
                    self.assertNotEqual(value - initial_value, 0)
                    self.assertFalse(epoch == initial_epoch and value == initial_value)
            for before, after in itertools.product([0, 1], repeat=2):
                if before == after:
                    self.assertEqual(after - before, 0)

    def test_invalid_family_parameters_are_rejected(self):
        with self.assertRaises(ValueError):
            generator.write_skew(2, False)
        for modulus in [0, 1, 2, 4]:
            with self.assertRaises(ValueError):
                generator.aba(modulus, False)


if __name__ == "__main__":
    unittest.main()
