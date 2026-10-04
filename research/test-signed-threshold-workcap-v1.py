"""Metadata and mocked launch guards only; never execute a solver."""
from contextlib import redirect_stderr
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text())


spec = importlib.util.spec_from_file_location('launcher', ROOT / 'research/launch-signed-threshold-workcap-v1.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class DiagnosticPreparationTests(unittest.TestCase):
    def test_exact_selection_and_parent_denominators(self):
        summary = read(ROOT / 'research/signed-threshold-full-v1-summary.json')
        plan = read(launcher.PLAN)
        selection_path = ROOT / 'research/signed-threshold-workcap-v1-selection.json'
        selection = read(selection_path)
        manifest = read(ROOT / 'benchmarks/signed-threshold-workcap-v1/manifest.json')
        expected = sorted(set(summary['historical_complementarity']['baseline_unknown']) | set(summary['unary_only']))
        self.assertEqual(len(expected), 10)
        self.assertEqual(plan['queries'], expected)
        self.assertEqual(selection['queries'], expected)
        self.assertEqual([q['name'] for q in manifest['queries']], expected)
        self.assertEqual(plan['rows'], 20)
        for record in (selection, plan, manifest):
            self.assertEqual(record['parent_denominators'], dict(source_slots=656, imported_slots=640, unavailable_slots=16))
        self.assertEqual(plan['selection_sha256'], hashlib.sha256(selection_path.read_bytes()).hexdigest())
        parent = read(ROOT / 'benchmarks/application-portfolio-comparison-v1/manifest.json')
        index = {q['name']: q for q in parent['queries']}
        self.assertEqual(manifest['queries'], [index[name] for name in expected])

    def test_only_corpus_work_cap_and_output_differ(self):
        plan = read(launcher.PLAN)
        parent = read(ROOT / 'research/signed-threshold-full-v1-plan.json')
        command = list(parent['command'])
        for flag in ('--corpus', '--max-states', '--output'):
            command[command.index(flag) + 1] = plan['command'][plan['command'].index(flag) + 1]
        self.assertEqual(command, plan['command'])
        self.assertEqual(plan['command'][plan['command'].index('--max-states') + 1], '100000000')
        self.assertEqual(plan['binary_sha256'], parent['binary_sha256'])
        for name, digest in parent['file_sha256'].items():
            if name.startswith(('results/solver-signed-threshold-v1/', 'results/runner-threshold-v1/')):
                self.assertEqual(plan['file_sha256'][name], digest)
        for name, digest in plan['file_sha256'].items():
            if name.startswith('research/') or name.endswith('/manifest.json'):
                self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest)

    def test_explicit_launch_required(self):
        with patch.object(sys, 'argv', ['launcher']), patch.object(launcher.subprocess, 'Popen') as spawn, \
             redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            launcher.main()
        self.assertEqual(error.exception.code, 2)
        spawn.assert_not_called()

    def test_no_overwrite_and_idle_preflight_before_spawn(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            output = base / 'output'
            plan = base / 'plan.json'
            plan.write_text(json.dumps(dict(command=['mock', '--output', str(output)])))
            output.mkdir()
            with patch.object(sys, 'argv', ['launcher', '--launch']), \
                 patch.object(launcher, 'PLAN', plan), patch.object(launcher, 'PREFIX', base / 'receipt'), \
                 patch.object(launcher.subprocess, 'Popen') as spawn, patch.object(launcher, 'idle') as idle:
                with self.assertRaises(FileExistsError):
                    launcher.main()
                spawn.assert_not_called()
                idle.assert_not_called()
                output.rmdir()
                idle.side_effect = RuntimeError('mock conflicting workload')
                with self.assertRaisesRegex(RuntimeError, 'mock conflicting workload'):
                    launcher.main()
                spawn.assert_not_called()
                self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
