import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from external_verdict import admit, parse
import process_runner
import verifypn_runner


class AdmissionTests(unittest.TestCase):
    def test_exact_id_and_both_polarities(self):
        text = 'FORMULA other TRUE TECHNIQUES X\nFORMULA a.+ FALSE TECHNIQUES X TIME 0.1\n'
        self.assertEqual(parse(text, 'a.+', 'EF', 0, False)['verdict'], 'unreachable')
        self.assertEqual(parse(text, 'a.+', 'AG', 0, False)['verdict'], 'reachable')
        self.assertEqual(parse(text, 'a', 'EF', 0, False)['verdict'], 'unknown')

    def test_output_never_overrides_failed_or_late_execution(self):
        for code, expired, wall in [(1, False, 0.1), (-9, True, 5.01), (0, False, 5.001), (None, False, 0.1)]:
            with self.subTest(code=code, expired=expired, wall=wall):
                result = parse('FORMULA p TRUE\n', 'p', 'EF', code, expired, wall=wall, seconds=5)
                self.assertEqual(result['verdict'], 'unknown')
                self.assertEqual(result['observed_verdict'], 'reachable')
                self.assertTrue(result['admission_failures'])

    def test_failure_diagnostics_survive_a_valid_formula_line(self):
        for failure in ['Traceback (most recent call last):', 'ERROR: tool failed',
                        'java.lang.IllegalArgumentException: bad query', 'integer overflow',
                        'unsupported target', 'CANNOT_COMPUTE', 'walk: command not found',
                        'No such file or directory', 'error: 4ti2 failed']:
            with self.subTest(failure=failure):
                result = parse('FORMULA p TRUE\n' + failure, 'p', 'EF', 0, False)
                self.assertEqual(result['verdict'], 'unknown')
                self.assertIn(failure, result['capability_failures'])
        self.assertEqual(parse('0 errors\nFORMULA p TRUE TECHNIQUES X\n', 'p', 'EF', 0, False)['verdict'], 'reachable')

    def test_malformed_conflicting_missing_and_unsupported_are_unknown(self):
        for text in ['FORMULA p TRUE\nFORMULA p FALSE\n', 'FORMULA p TRUE\nFORMULA p MAYBE\n',
                     'FORMULA p TRUE trailing-garbage\n', 'FORMULA other TRUE\n', '']:
            self.assertEqual(parse(text, 'p', 'EF', 0, False)['verdict'], 'unknown')
        self.assertEqual(parse('FORMULA p TRUE\n', 'p', 'LTL', 0, False)['verdict'], 'unknown')

    def test_final_admission_applies_to_native_and_all_external_methods(self):
        for method in ('native-excess', 'verifypn-default', 'smpt-mcc-portable', 'its-mcc'):
            result = admit(dict(method=method, verdict='reachable', wall_seconds=5.01,
                                exit_code=0, outer_timeout=False), 5)
            self.assertEqual(result['verdict'], 'unknown')
            self.assertEqual(result['observed_verdict'], 'reachable')
        result = admit(dict(verdict='error', error='invalid certificate', exit_code=0), 5)
        self.assertEqual(result['verdict'], 'unknown')
        self.assertEqual(result['error'], 'invalid certificate')
        self.assertEqual(result['observed_verdict'], 'error')


class VerifyPNTests(unittest.TestCase):
    def test_selector_validation_is_common_preflight(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'property.xml'
            for xml in ['<property-set><property><id>p</id></property></property-set>',
                        '<property-set xmlns="urn:mcc"><property><id>p</id></property></property-set>']:
                path.write_text(xml)
                verifypn_runner.check_single_property(path, 'p')
            for xml in ['<property-set/>', '<property-set><property><id>other</id></property></property-set>',
                        '<property-set><property><id>p</id></property><property><id>q</id></property></property-set>']:
                path.write_text(xml)
                with self.assertRaises(ValueError):
                    verifypn_runner.check_single_property(path, 'p')

    def test_constant_selector_and_strict_wall(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            args = SimpleNamespace(verifypn_binary=root/'verifypn-linux64', verifypn_root=root,
                                   outer_grace=0, seconds=5)
            query = dict(name='q', xml='not-read-before-execute.xml', pnml='model.pnml', property_id='p', kind='AG')
            commands = []
            def execute(command, cwd, seconds, output, options):
                commands.append(command)
                self.assertEqual(seconds, 5)
                output.write_text('FORMULA p FALSE TECHNIQUES X\n')
                return 5.01, 0, False, {}
            result = verifypn_runner.run(query, root, root, 'verifypn-default', 0, args, execute)
            self.assertEqual(commands[0][1:3], ['-x', '1'])
            self.assertEqual(result['verdict'], 'unknown')
            self.assertEqual(result['observed_verdict'], 'reachable')


class WorkloadTests(unittest.TestCase):
    def test_java_its_greatspn_and_versioned_names_but_not_validators(self):
        def process(name, argv, cwd='/workspace/project'):
            p = mock.Mock()
            p.name.return_value = name
            p.cmdline.return_value = argv
            p.cwd.return_value = cwd
            p.status.return_value = 'running'
            p.create_time.return_value = 1
            return p
        found = [process('java', ['/usr/bin/java', '-jar', 'its.jar']),
                 process('its-reach', ['/tools/its-reach-linux64']),
                 process('RGMEDD.5', ['/tools/RGMEDD.5']),
                 process('python', ['/venv/python', 'its_original.py', '--runtime-config', 'r.json']),
                 process('verifypn-linux64', ['/tools/verifypn-linux64']),
                 process('python', ['/venv/python', '-m', 'smpt'])]
        ignored = [process('python', ['/venv/python', 'bounded_validation.py']),
                   process('python', ['/venv/python', 'benchmark_smpt_classic.py']),
                   process('java', ['/usr/bin/java', '-jar', 'unrelated.jar'], '/elsewhere')]
        with mock.patch.object(process_runner.psutil, 'process_iter', return_value=found+ignored):
            self.assertEqual(len(process_runner.workspace_workloads('/workspace')), len(found))


class HarnessTests(unittest.TestCase):
    def test_smpt_qualified_command_and_failure_with_formula(self):
        import benchmark_smpt_classic as harness
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            args = SimpleNamespace(smpt_original=True, smpt_python=root/'python',
                                   smpt_root=root/'SMPT', auto_reduce=False, seconds=5,
                                   outer_grace=0, linux_cpus=[8])
            query = dict(name='q', pnml='../original/model.pnml', xml='../original/p.xml',
                         property_id='p', kind='AG')
            def execute(command, cwd, seconds, output, options):
                self.assertEqual(cwd, args.smpt_root)
                self.assertEqual(seconds, 5)
                self.assertIn('--mcc', command)
                self.assertIn('--auto-reduce', command)
                self.assertEqual(command[:3], [str(args.smpt_python), '-m', 'smpt'])
                self.assertEqual(command[command.index('-n')+1], str(root/'../original/model.pnml'))
                output.write_text('FORMULA p FALSE TECHNIQUES SAT_SMT\nTraceback (most recent call last):\n')
                return 0.5, 0, False, {}
            with mock.patch.object(harness, 'execute', side_effect=execute):
                result = harness.smpt(query, root, root, 'smpt-mcc-portable', 0, args)
            self.assertEqual(result['verdict'], 'unknown')
            self.assertEqual(result['observed_verdict'], 'reachable')
            self.assertEqual(result['scheduling_policy'], 'official-mcc')

    def test_native_nonzero_and_late_results_skip_certificate_worker(self):
        import benchmark_smpt_classic as harness
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            args = SimpleNamespace(native_tools={'native-excess':dict(binary=str(root/'solver'), engine='portfolio-excess')},
                                   seconds=5, max_states=2000000, outer_grace=0)
            query = dict(name='q', pnml='model.pnml', xml='p.xml', property_id='p')
            for wall, code, expired in [(0.1, 1, False), (5.01, 0, False), (4, 0, True)]:
                with mock.patch.object(harness, 'execute', return_value=(wall, code, expired, {})), \
                     mock.patch('bounded_validation.run_validation') as validation:
                    result = harness.rust_original(query, root, root, 'native-excess', 0, args)
                    self.assertEqual(result['verdict'], 'unknown')
                    validation.assert_not_called()

    def test_its_command_includes_staging_in_execute_and_rechecks_logs(self):
        import its_runner
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            args = SimpleNamespace(native_python=root/'python', its_runtime_config=root/'runtime.json',
                                   workspace_root=root, seconds=5, outer_grace=0)
            query = dict(name='q', pnml='model.pnml', xml='p.xml', property_id='p', kind='EF')
            cases = [('FORMULA p TRUE TECHNIQUES X\n',0,0,0.2,'reachable'),
                     ('FORMULA p TRUE\nTraceback (most recent call last):\n',0,0,0.2,'unknown'),
                     ('FORMULA p TRUE\n',0,1,0.2,'unknown'),
                     ('FORMULA p TRUE\n',1,0,0.2,'unknown'),
                     ('FORMULA p TRUE\n',0,0,5.01,'unknown'),
                     ('FORMULA p TRUE\nFORMULA p MAYBE\n',0,0,0.2,'unknown')]
            for index, (text, wrapper_code, tool_code, wall, expected) in enumerate(cases):
                def execute(command, cwd, seconds, output, options):
                    self.assertFalse((root/'model.pnml').exists())
                    self.assertEqual(seconds, 5)
                    self.assertEqual(cwd, root)
                    self.assertEqual(Path(command[1]).name, 'its_original.py')
                    self.assertEqual(command[command.index('--runtime-config')+1], str(args.its_runtime_config))
                    artifacts = Path(command[command.index('--artifacts')+1])
                    self.assertFalse(artifacts.exists())
                    artifacts.mkdir()
                    (artifacts/'tool.log').write_text(text)
                    output.write_text(json.dumps(dict(kind='its-original-v1', property_id='p', property_kind='EF',
                        verdict='reachable', property_truth=True, tool_exit_code=tool_code,
                        timed_out=False, stage_seconds=0.01, tool_seconds=0.1,
                        parse_seconds=0.001, total_seconds=0.12, capability_failures=[], errors=[])))
                    return wall, wrapper_code, False, {}
                result = its_runner.run(query, root, root, 'its-mcc', index, args, execute)
                self.assertEqual(result['verdict'], expected)
                self.assertEqual(len(result['underlying_logs']), 1)
                self.assertTrue(result['observed_formula_results'])

    def test_its_missing_or_malformed_output_stays_unknown(self):
        import its_runner
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            args = SimpleNamespace(native_python=root/'python', its_runtime_config=root/'runtime.json',
                                   workspace_root=root, seconds=5, outer_grace=0)
            query = dict(name='q', pnml='model.pnml', xml='p.xml', property_id='p', kind='EF')
            def execute(command, cwd, seconds, output, options):
                output.write_text('{"partial":')
                return 0.1, 0, False, {}
            result = its_runner.run(query, root, root, 'its-mcc', 0, args, execute)
            self.assertEqual(result['verdict'], 'unknown')
            self.assertIn('invalid-wrapper-result', result['admission_failures'])
            self.assertIn('missing-underlying-tool-log', result['admission_failures'])

    def test_its_unreadable_log_and_invalid_exit_code_stay_unknown(self):
        import its_runner
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            args = SimpleNamespace(native_python=root/'python', its_runtime_config=root/'runtime.json',
                                   workspace_root=root, seconds=5, outer_grace=0)
            query = dict(name='q', pnml='model.pnml', xml='p.xml', property_id='p', kind='EF')
            for index, code in enumerate((0, False)):
                def execute(command, cwd, seconds, output, options):
                    artifacts = Path(command[command.index('--artifacts')+1])
                    artifacts.mkdir()
                    (artifacts/'tool.log').write_text('FORMULA p TRUE\n')
                    output.write_text(json.dumps(dict(kind='its-original-v1', property_id='p', property_kind='EF',
                        verdict='reachable', property_truth=True, tool_exit_code=code,
                        timed_out=False, stage_seconds=0.01, tool_seconds=0.1,
                        parse_seconds=0.001, total_seconds=0.12, capability_failures=[], errors=[])))
                    return 0.2, 0, False, {}
                with mock.patch.object(Path, 'read_bytes', side_effect=PermissionError('denied')):
                    result = its_runner.run(query, root, root, 'its-mcc', index, args, execute)
                self.assertEqual(result['verdict'], 'unknown')
                self.assertIn('unreadable-underlying-tool-log', result['admission_failures'])
                self.assertEqual(result['underlying_log_error'], 'denied')
                if code is False:
                    self.assertIn('invalid-wrapper-result', result['admission_failures'])


if __name__ == '__main__':
    unittest.main()
