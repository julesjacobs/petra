"""Mock-only runner and qualification metadata checks; no external execution."""
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prior_tests = load('prior_tests', 'research/test-smpt-single-core-runner-v1.py')
runner = load('new_runner', 'results/runner-smpt-single-core-v2/source/scripts/benchmark_smpt_classic.py')
launcher = load('qualification_launcher', 'research/run-general-development-v3-linux-v1.py')
prior_tests.runner = runner


class RunnerTests(prior_tests.MockRunnerTests):
    def test_parent_hashes_and_reproducible_archive(self):
        import hashlib
        old = json.loads((ROOT / 'results/runner-smpt-single-core-v1/files-sha256.json').read_text())
        new = json.loads((ROOT / 'results/runner-smpt-single-core-v2/files-sha256.json').read_text())
        self.assertEqual([n for n in old if old[n] != new[n]], ['scripts/benchmark_smpt_classic.py'])
        for folder, manifest in [('runner-smpt-single-core-v1', old), ('runner-smpt-single-core-v2', new)]:
            for name, digest in manifest.items():
                self.assertEqual(hashlib.sha256((ROOT / 'results' / folder / 'source' / name).read_bytes()).hexdigest(), digest)

    def test_workload_scope_uses_explicit_common_root(self):
        common = Path('/mock/common')
        for cpus in ([8], None):
            checker = Mock(return_value=[])
            run = Mock(return_value=(1, 0, False, {}))
            modules = {'linux_runner': SimpleNamespace(run=run),
                       'process_runner': SimpleNamespace(run=run, workspace_workloads=checker)}
            args = SimpleNamespace(workspace_root=common, linux_cpus=cpus, track_resources=True,
                                   memory_mib=2048, perf=True)
            with patch.dict(sys.modules, modules):
                runner.execute(['mock'], Path('/mock/cwd'), 5, Path('/mock/log'), args)
                checker.assert_called_once_with(common)
                run.assert_called_once()
                run.reset_mock()
                checker.return_value = [dict(pid=123, name='mock')]
                with self.assertRaises(RuntimeError):
                    runner.execute(['mock'], Path('/mock/cwd'), 5, Path('/mock/log'), args)
                run.assert_not_called()


class QualificationTests(unittest.TestCase):
    def test_controls_counts_and_paths(self):
        plan = json.loads((ROOT / 'research/general-development-v3-linux-v1/plan.json').read_text())
        old = json.loads((ROOT / 'research/application-walk-full-v1/plan.json').read_text())
        self.assertEqual(len(plan['methods']), 9)
        self.assertEqual(plan['expected_rows'], plan['properties'] * len(plan['methods']))
        self.assertEqual(plan['properties'], 176)
        self.assertEqual(plan['exact_ordered_branch_representatives'], 175)
        self.assertEqual(plan['native_tools'], old['native_tools'])
        self.assertEqual(plan['buffer_agglomeration_methods'], old['buffer_agglomeration_methods'])
        cmd = launcher.command(plan)
        for flag in ['--workspace-root', '--corpus', '--binary', '--native-python', '--smpt-root',
                     '--smpt-python', '--verifypn-binary', '--verifypn-root', '--output']:
            self.assertTrue(cmd[cmd.index(flag) + 1].startswith(str(launcher.REMOTE)))
        self.assertEqual(cmd[2], str(launcher.REMOTE / plan['runner_source'] / 'scripts/benchmark_smpt_classic.py'))
        self.assertEqual(cmd[cmd.index('--linux-cpus') + 1], '8')
        self.assertEqual(cmd[cmd.index('--seconds') + 1], '5')
        self.assertIn('--perf', cmd)
        self.assertEqual(plan['capability_preflight']['status'], 'pending')
        self.assertFalse((ROOT / plan['output']).exists())
        for name in plan['required_file_sha256']:
            if name.startswith('benchmarks/'):
                self.assertTrue(name.startswith('benchmarks/general-development-v3/'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
