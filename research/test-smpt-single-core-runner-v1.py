"""Mock-only command/parser/preflight checks; no solver processes or models."""
from contextlib import redirect_stderr, redirect_stdout
import argparse
import ast
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
NEW = ROOT / 'results/runner-smpt-single-core-v1'
PARENT = ROOT / 'results/runner-threshold-v1'
sys.path.insert(0, str(NEW / 'source/scripts'))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = load('new_runner', NEW / 'source/scripts/benchmark_smpt_classic.py')
parent = load('parent_runner', PARENT / 'source/scripts/benchmark_smpt_classic.py')
preparer = load('preparer', ROOT / 'research/prepare-smpt-single-core-runner-v1.py')


class MockRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.args = SimpleNamespace(smpt_python=Path('/mock/python'), smpt_original=True,
            auto_reduce=False, seconds=5.25, outer_grace=0, smpt_root=Path('/mock/smpt'),
            linux_cpus=[8])
        self.query = dict(name='mock-query', pnml='original.pnml', xml='original.xml',
                          net='translated.net', property='translated.xml', property_id='ID.+[1]', kind='EF')

    def call(self, method, *, module=runner, contents=None, wall=1, code=0, expired=False):
        if contents is None:
            contents = 'FORMULA ID.+[1] TRUE TECHNIQUES MOCK\n'
        def execute(command, cwd, seconds, output, args):
            output.write_text(contents)
            return wall, code, expired, {'mocked': True}
        with patch.object(module, 'execute', side_effect=execute) as mocked:
            result = module.smpt(self.query, self.path, self.path, method, 0, self.args)
            self.assertEqual(mocked.call_count, 1)
            self.assertEqual(mocked.call_args.args[1:3], (self.args.smpt_root, self.args.seconds))
        return result

    def test_added_commands_and_row_metadata(self):
        for method, methods in runner.SMPT_SINGLE_CORE_MODES.items():
            with self.subTest(method=method):
                row = self.call(method)
                command = row['command']
                self.assertEqual(row['verdict'], 'reachable')
                self.assertEqual(command[:3], ['/mock/python', '-m', 'smpt'])
                self.assertEqual(command[command.index('-n') + 1], str(self.path / 'original.pnml'))
                self.assertEqual(command[command.index('--xml') + 1], str(self.path / 'original.xml'))
                self.assertEqual(command[command.index('--timeout') + 1], '6')
                self.assertEqual(command.count('--auto-reduce'), 1)
                self.assertNotIn('--project', command)
                self.assertNotIn('enabled_methods', row)
                self.assertEqual(row['requested_methods'], methods)
                self.assertIsNone(row['effective_workers'])
                if method == 'smpt-mcc-portable':
                    self.assertIn('--mcc', command)
                    self.assertEqual(command[command.index('--methods')+1:command.index('--mcc')], methods)
                    self.assertFalse(row['requested_methods_control_workers'])
                    self.assertEqual(row['scheduling_policy'], 'official-mcc')
                else:
                    self.assertNotIn('--mcc', command)
                    self.assertEqual(command[command.index('--methods')+1:command.index('--timeout')], methods)
                    self.assertEqual(row['scheduling_policy'], 'requested-method-portfolio')

    def test_property_polarity(self):
        for method in runner.SMPT_SINGLE_CORE_MODES:
            for kind in ('EF', 'AG'):
                for truth in (True, False):
                    with self.subTest(method=method, kind=kind, truth=truth):
                        self.query['kind'] = kind
                        row = self.call(method, contents=f'FORMULA ID.+[1] {str(truth).upper()}\n')
                        expected = 'reachable' if truth == (kind == 'EF') else 'unreachable'
                        self.assertEqual(row['verdict'], expected)
                        self.assertEqual(runner.property_truth(kind, row['verdict']), truth)

    def test_commands_accepted_by_actual_smpt_argument_parser(self):
        source = ROOT / 'vendor/SMPT-portable/smpt/smpt.py'
        tree = ast.parse(source.read_text())
        main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
        statements = []
        for node in main.body:
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'results' for t in node.targets):
                break
            if statements or (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'parser' for t in node.targets)):
                statements.append(node)
        namespace = {'ArgumentParser': argparse.ArgumentParser}
        exec(compile(ast.Module(body=statements, type_ignores=[]), str(source), 'exec'), namespace)
        parser = namespace['parser']
        for method in runner.SMPT_SINGLE_CORE_MODES:
            with self.subTest(method=method):
                command = self.call(method)['command']
                parsed = parser.parse_args(command[3:])
                self.assertEqual(parsed.mcc, method == 'smpt-mcc-portable')
                self.assertEqual(parsed.methods, runner.SMPT_MODES[method])
                self.assertTrue(parsed.auto_reduce)
                self.assertFalse(parsed.project)
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parser.parse_args(['-n', 'mock.pnml', '--mcc'])

    def test_wrong_property_id_and_conflicts(self):
        for method in runner.SMPT_SINGLE_CORE_MODES:
            for contents, verdict in [
                ('FORMULA OTHER TRUE\n', 'unknown'),
                ('FORMULA ID.+[1]suffix TRUE\n', 'unknown'),
                ('FORMULA IDxx1 TRUE\n', 'unknown'),
                ('FORMULA OTHER FALSE\nFORMULA ID.+[1] TRUE\n', 'reachable'),
                ('FORMULA ID.+[1] TRUE\nFORMULA ID.+[1] FALSE\n', 'error'),
                ('FORMULA ID.+[1] TRUE\nFORMULA ID.+[1] TRUE\n', 'reachable'),
            ]:
                with self.subTest(method=method, contents=contents):
                    row = self.call(method, contents=contents)
                    self.assertEqual(row['verdict'], verdict)
                    if verdict == 'unknown':
                        self.assertIsNone(row['formula_output'])
                    else:
                        self.assertTrue(row['formula_output'].startswith('FORMULA ID.+[1] '))

    def test_late_answers_rejected_on_both_platforms(self):
        for method in runner.SMPT_SINGLE_CORE_MODES:
            for cpus in (None, [8]):
                self.args.linux_cpus = cpus
                for wall, expired in [(1, True), (5.251, False), (5.251, True)]:
                    with self.subTest(method=method, cpus=cpus, wall=wall, expired=expired):
                        row = self.call(method, wall=wall, expired=expired)
                        self.assertEqual(row['verdict'], 'unknown')
                        self.assertTrue(row['outer_timeout'])
                row = self.call(method, wall=5.25)
                self.assertEqual(row['verdict'], 'reachable')
                self.assertFalse(row['outer_timeout'])

    def test_capability_errors_retained(self):
        for method in runner.SMPT_SINGLE_CORE_MODES:
            row = self.call(method, contents='qsolve: command not found\n', code=1)
            self.assertEqual(row['verdict'], 'error')
            self.assertEqual(row['capability_failures'], ['qsolve: command not found'])
            row = self.call(method, contents='Traceback (most recent call last):\n', code=0)
            self.assertEqual(row['verdict'], 'error')
            self.assertTrue(row['subprocess_error'])

    def test_existing_commands_and_results_unchanged(self):
        for method in parent.SMPT_MODES:
            for original in (False, True):
                self.args.smpt_original = original
                for cpus in (None, [8]):
                    self.args.linux_cpus = cpus
                    for wall, expired, contents, code in [
                        (1, False, 'FORMULA ID.+[1] TRUE\n', 0),
                        (6, True, 'FORMULA ID.+[1] TRUE\n', 0),
                        (1, False, 'FORMULA WRONG TRUE\n', 0),
                        (1, False, 'command not found\n', 1),
                    ]:
                        with self.subTest(method=method, original=original, cpus=cpus, expired=expired):
                            kwargs = dict(wall=wall, expired=expired, contents=contents, code=code)
                            self.assertEqual(self.call(method, **kwargs), self.call(method, module=parent, **kwargs))

    def main_mock(self, method, *, resources=True, missing=False, marker=True, unavailable=False):
        corpus = self.path / 'corpus'
        corpus.mkdir(exist_ok=True)
        queries = [dict(name='unavailable', suite='mock', status='unavailable', observed=False,
                        property_slot=0)] if unavailable else []
        (corpus / 'manifest.json').write_text(json.dumps(dict(queries=queries)))
        smpt_root = self.path / 'smpt'
        (smpt_root / 'smpt/interfaces').mkdir(parents=True, exist_ok=True)
        walk = smpt_root / 'smpt/interfaces/walk.py'
        walk.write_text('# mock source\n')
        if marker:
            (smpt_root / 'PORTABILITY.json').write_text(json.dumps(dict(
                patched_sha256=hashlib.sha256(walk.read_bytes()).hexdigest())))
        fake_binary = self.path / 'fake-executable'
        fake_binary.write_text('Never executed.\n')
        output = self.path / method
        argv = ['mock', '--methods', method, '--corpus', str(corpus), '--output', str(output),
                '--binary', str(fake_binary), '--native-python', str(fake_binary),
                '--smpt-root', str(smpt_root)]
        if resources:
            argv.append('--track-resources')
        with patch.object(sys, 'argv', argv), patch.dict('os.environ'), \
             patch.object(runner.shutil, 'which', return_value=None if missing else str(fake_binary)), \
             patch.object(runner.subprocess, 'run', return_value=SimpleNamespace(stdout='', stderr='')) as dependency_help, \
             patch.object(runner, 'execute', side_effect=AssertionError('No execution permitted')), \
             redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            runner.main()
        self.assertEqual(sum(c.args == (['walk', '-h'],) for c in dependency_help.call_args_list), 1)
        return json.loads((output / 'environment.json').read_text())

    def test_environment_marks_requested_methods_and_official_scheduling(self):
        for method in runner.SMPT_SINGLE_CORE_MODES:
            with self.subTest(method=method):
                env = self.main_mock(method)
                self.assertEqual(env['queries'], 0)
                self.assertEqual(env['smpt_scheduling'][method], runner.smpt_scheduling(method))
                self.assertTrue(env['smpt_auto_reduce_by_method'][method])

    def test_new_modes_require_resource_tracking(self):
        for method in runner.SMPT_SINGLE_CORE_MODES:
            with self.subTest(method=method), self.assertRaises(SystemExit) as exit:
                self.main_mock(method, resources=False)
            self.assertEqual(exit.exception.code, 2)

    def test_unavailable_rows_preserve_configuration_metadata(self):
        for method in runner.SMPT_SINGLE_CORE_MODES:
            with self.subTest(method=method):
                self.main_mock(method, unavailable=True)
                row = json.loads((self.path / method / 'runs.jsonl').read_text())
                self.assertEqual(row['verdict'], 'unsupported')
                self.assertFalse(row['execution_attempted'])
                for key, value in runner.smpt_scheduling(method).items():
                    self.assertEqual(row[key], value)

    def test_new_modes_require_portable_dependencies(self):
        for method in runner.SMPT_SINGLE_CORE_MODES:
            with self.subTest(method=method), self.assertRaises(SystemExit) as exit:
                self.main_mock(method, missing=True)
            self.assertEqual(exit.exception.code, 2)

    def test_new_modes_require_portable_marker(self):
        for method in runner.SMPT_SINGLE_CORE_MODES:
            with self.subTest(method=method), self.assertRaises(SystemExit) as exit:
                self.main_mock(method, marker=False)
            self.assertEqual(exit.exception.code, 2)

    def test_parent_hashes_and_reproducible_archive(self):
        parents = json.loads((PARENT / 'files-sha256.json').read_text())
        files = json.loads((NEW / 'files-sha256.json').read_text())
        self.assertEqual(len(parents), 24)
        for name, expected in parents.items():
            self.assertEqual(hashlib.sha256((PARENT / 'source' / name).read_bytes()).hexdigest(), expected)
        for name, expected in files.items():
            self.assertEqual(hashlib.sha256((NEW / 'source' / name).read_bytes()).hexdigest(), expected)
        self.assertEqual([name for name in parents if parents[name] != files[name]],
                         ['scripts/benchmark_smpt_classic.py'])
        copy = self.path / 'prepared-again'
        provenance = preparer.prepare(copy)
        self.assertEqual((copy / 'runner.tar.gz').read_bytes(), (NEW / 'runner.tar.gz').read_bytes())
        self.assertEqual(provenance, json.loads((NEW / 'provenance.json').read_text()))


if __name__ == '__main__':
    unittest.main(verbosity=2)
