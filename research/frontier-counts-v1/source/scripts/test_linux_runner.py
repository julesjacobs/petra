import os
import errno
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from linux_runner import PerfUnavailable, _remember_processes, parse_perf, run


class CgroupRaceTests(unittest.TestCase):
    def test_disappeared_group(self):
        for code in (errno.ENOENT, errno.ENODEV):
            with self.subTest(errno=code), patch.object(Path, 'read_text', side_effect=OSError(code, 'gone')):
                known = {}
                _remember_processes({'ControlGroup': '/test'}, known)
                self.assertEqual(known, {})

    def test_other_errors_propagate(self):
        for code in (errno.EACCES, errno.EIO):
            with self.subTest(errno=code), patch.object(Path, 'read_text', side_effect=OSError(code, 'failed')):
                with self.assertRaises(OSError) as failure:
                    _remember_processes({'ControlGroup': '/test'}, {})
                self.assertEqual(failure.exception.errno, code)


class PerfParserTests(unittest.TestCase):
    def test_counters_preserve_running_percent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'perf.csv'
            path.write_text('123;;instructions:u;1000000;87.50;;\n'
                            '456;;cycles:u;1000000;87.50;;\n'
                            '1.25;msec;task-clock;1250000;100.00;;\n')
            counters = parse_perf(path)
            self.assertEqual(counters['instructions:u']['value'], 123)
            self.assertEqual(counters['instructions:u']['time_running_percent'], 87.5)
            self.assertEqual(counters['task-clock']['value'], 1.25)

    def test_missing_and_unavailable_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'perf.csv'
            for content in ('', '<not supported>;;instructions:u;0;0;;\n'):
                path.write_text(content)
                with self.assertRaises(PerfUnavailable):
                    parse_perf(path)


@unittest.skipUnless(sys.platform == 'linux' and os.environ.get('PVASS_TEST_LINUX') == '1',
                     'requires an explicitly selected Linux systemd user test host')
class LinuxRunnerTests(unittest.TestCase):
    def setUp(self):
        root = Path(os.environ['PVASS_LINUX_TEST_DIRECTORY']).resolve()
        root.mkdir(parents=True, exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(dir=root)
        self.addCleanup(self.directory.cleanup)
        self.cwd = Path(self.directory.name)
        self.cpu = int(os.environ.get('PVASS_TEST_CPU', '8'))

    def invoke(self, source, seconds=3, memory=128 * 1024**2, perf=False):
        result = run([sys.executable, '-c', source], self.cwd, seconds,
                     self.cwd / 'output.log', memory, cpus=[self.cpu], perf=perf)
        self.assertIsNotNone(result[3]['cpu_seconds'])
        self.assertIsNotNone(result[3]['peak_memory_bytes'])
        self.assertIn(result[3]['systemd_properties']['SubState'], ('exited', 'failed', 'dead'))
        return result

    def test_success_affinity_and_accounting(self):
        wall, code, expired, usage = self.invoke(
            'import os; print(sorted(os.sched_getaffinity(0))); sum(i*i for i in range(100000))')
        self.assertEqual(code, 0)
        self.assertFalse(expired)
        self.assertEqual((self.cwd / 'output.log').read_text().strip(), str([self.cpu]))
        self.assertGreater(usage['cpu_seconds'], 0)
        self.assertGreater(usage['peak_memory_bytes'], 0)
        self.assertGreater(int(usage['systemd_properties']['ExecMainExitTimestampMonotonic']), 0)

    def test_failed_exit(self):
        _, code, expired, usage = self.invoke('raise SystemExit(7)')
        self.assertEqual(code, 7)
        self.assertFalse(expired)
        self.assertEqual(usage['systemd_result'], 'exit-code')

    def test_python_virtual_environment_is_preserved(self):
        for perf in (False, True):
            _, code, expired, _ = self.invoke('import sys; print(sys.prefix)', perf=perf)
            self.assertEqual(code, 0)
            self.assertFalse(expired)
            self.assertEqual((self.cwd / 'output.log').read_text().strip(), sys.prefix)

    def test_timeout_detached_descendant(self):
        source = """import os, subprocess, sys
child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], start_new_session=True)
open('descendant.pid', 'w').write(str(child.pid))
import time
time.sleep(60)
"""
        wall, _, expired, usage = self.invoke(source, seconds=0.3)
        self.assertTrue(expired)
        self.assertEqual(usage['systemd_result'], 'timeout')
        self.assertLess(wall, 5)
        pid = int((self.cwd / 'descendant.pid').read_text())
        stat = Path(f'/proc/{pid}/stat')
        self.assertTrue(not stat.exists() or stat.read_text().split(') ')[1].startswith('Z'))

    def test_normal_parent_exit_cleans_up_detached_children_without_timeout(self):
        source = """import subprocess, sys
child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], start_new_session=True)
open('descendant.pid', 'w').write(str(child.pid))
"""
        wall, code, expired, usage = self.invoke(source, seconds=3, perf=True)
        self.assertEqual(code, 0)
        self.assertFalse(expired)
        self.assertEqual(usage['systemd_result'], 'success')
        self.assertLess(wall, 2)
        pid = int((self.cwd / 'descendant.pid').read_text())
        stat = Path(f'/proc/{pid}/stat')
        self.assertTrue(not stat.exists() or stat.read_text().split(') ')[1].startswith('Z'))

    def test_memory_oom(self):
        _, _, expired, usage = self.invoke('x = bytearray(512 * 1024**2)', memory=64 * 1024**2)
        self.assertTrue(expired)
        self.assertTrue(usage['memory_limit_exceeded'])
        self.assertEqual(usage['systemd_result'], 'oom-kill')

    def test_perf_timeout_exports_counters(self):
        if int(Path('/proc/sys/kernel/perf_event_paranoid').read_text()) >= 3:
            self.skipTest('host disallows hardware counters')
        _, _, expired, usage = self.invoke('while True: pass', seconds=0.3, perf=True)
        self.assertTrue(expired)
        self.assertEqual(usage['systemd_result'], 'timeout')
        self.assertGreater(usage['perf_counters']['instructions:u']['value'], 0)

    def test_perf_oom_retains_failed_run_even_when_counters_are_lost(self):
        if int(Path('/proc/sys/kernel/perf_event_paranoid').read_text()) >= 3:
            self.skipTest('host disallows hardware counters')
        _, _, expired, usage = self.invoke('x = bytearray(512 * 1024**2)',
                                           memory=64 * 1024**2, perf=True)
        self.assertTrue(expired)
        self.assertTrue(usage['memory_limit_exceeded'])
        if usage['perf_counters'] is None:
            self.assertIn('perf_failure', usage)

    def test_perf_denied_is_explicit(self):
        fake = self.cwd / 'perf'
        fake.write_text('#!/bin/sh\necho "No permission to enable instructions:u event" >&2\nexit 255\n')
        fake.chmod(0o755)
        (self.cwd / 'output.log.perf.csv').write_text(
            '123;;instructions:u;10;100.00;;\n456;;cycles:u;10;100.00;;\n1;msec;task-clock;10;100.00;;\n')
        with patch.dict(os.environ, PATH=str(self.cwd) + os.pathsep + os.environ['PATH']):
            with self.assertRaisesRegex(PerfUnavailable, 'No permission'):
                self.invoke('open("solver-ran", "w").write("yes")', perf=True)
        self.assertFalse((self.cwd / 'solver-ran').exists())

    def test_perf_explicit_result(self):
        paranoid = int(Path('/proc/sys/kernel/perf_event_paranoid').read_text())
        if paranoid >= 3:
            with self.assertRaises(PerfUnavailable):
                self.invoke('sum(range(10000))', perf=True)
        else:
            _, code, expired, usage = self.invoke('sum(range(100000))', perf=True)
            self.assertEqual(code, 0)
            self.assertFalse(expired)
            self.assertGreater(usage['perf_counters']['instructions:u']['value'], 0)
            self.assertEqual(set(usage['perf_counters']), {'instructions:u', 'cycles:u', 'task-clock'})


if __name__ == '__main__':
    unittest.main(verbosity=2)
