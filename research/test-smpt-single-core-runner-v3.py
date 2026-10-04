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
runner = load('new_runner', 'results/runner-smpt-single-core-v3/source/scripts/benchmark_smpt_classic.py')
launcher = load('qualification_launcher', 'research/run-general-development-v3-linux-v1.py')
prior_tests.runner = runner


class RunnerTests(prior_tests.MockRunnerTests):
    def test_parent_hashes_and_reproducible_archive(self):
        import hashlib
        old = json.loads((ROOT / 'results/runner-smpt-single-core-v2/files-sha256.json').read_text())
        new = json.loads((ROOT / 'results/runner-smpt-single-core-v3/files-sha256.json').read_text())
        self.assertEqual([n for n in old if old[n] != new[n]], ['scripts/benchmark.py'])
        for folder, manifest in [('runner-smpt-single-core-v2', old), ('runner-smpt-single-core-v3', new)]:
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


class ClosureTests(unittest.TestCase):
    def test_exact_closure_and_invalid_claims(self):
        verifier = load('v3_verifier', 'results/runner-smpt-single-core-v3/source/scripts/benchmark.py')
        p = dict(places=['a','b'], initial=[1,0], transitions=[dict(name='move',pre=[[0,1]],post=[[1,1]])], target=[dict(coefficients=[0,1],bound=2,equality=True)])
        self.assertEqual(verifier.verify_proof(p,dict(kind='finite-closure-v1',states=2)), 'python-finite-closure')
        self.assertEqual(verifier.verify(p,dict(verdict='unreachable',reason='finite reachable state space exhausted')), 'python-finite-closure')
        for states in [0,1,3,200001,True]:
            with self.assertRaises(AssertionError):
                verifier.verify_proof(p,dict(kind='finite-closure-v1',states=states))
        with self.assertRaises(AssertionError):
            verifier.verify_proof(p,dict(kind='finite-closure-v1',states=2,extra=1))
        p['target'][0]['bound']=1
        with self.assertRaises(AssertionError):
            verifier.verify_proof(p,dict(kind='finite-closure-v1',states=2))


if __name__ == '__main__':
    unittest.main(verbosity=2)
