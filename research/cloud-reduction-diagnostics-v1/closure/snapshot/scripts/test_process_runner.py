import pathlib
import sys
import tempfile
import unittest
import time
from unittest import mock

import psutil

from process_runner import run


class RunnerTests(unittest.TestCase):
    def test_racing_environment_read_error_does_not_abort_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = pathlib.Path(directory)
            process = mock.Mock()
            process.info = {'create_time': time.time()}
            process.environ.side_effect = SystemError('racing macOS sysctl failure')
            with mock.patch('process_runner.psutil.process_iter', return_value=[process]):
                _, code, expired, _ = run([sys.executable, '-c', 'print(42)'], folder, 3, folder/'log')
            self.assertEqual(code, 0)
            self.assertFalse(expired)

    def test_immediately_orphaned_child_is_killed_after_normal_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = pathlib.Path(directory)
            pid = folder/'pid'
            script = ('import subprocess,sys,pathlib,os; '
                      'p=subprocess.Popen([sys.executable,"-c","import time; time.sleep(30)"],start_new_session=True); '
                      f'pathlib.Path({str(pid)!r}).write_text(str(p.pid)); os._exit(0)')
            _, code, expired, usage = run([sys.executable, '-c', script], folder, 3, folder/'log')
            self.assertEqual(code, 0)
            self.assertFalse(expired)
            self.assertGreaterEqual(usage['observed_processes'], 2)
            if psutil.pid_exists(int(pid.read_text())):
                self.assertEqual(psutil.Process(int(pid.read_text())).status(), psutil.STATUS_ZOMBIE)

    def test_detached_child_is_killed_on_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = pathlib.Path(directory)
            pid = folder/'pid'
            script = ('import subprocess,sys,time,pathlib; '
                      'p=subprocess.Popen([sys.executable,"-c","import time; time.sleep(30)"],start_new_session=True); '
                      f'pathlib.Path({str(pid)!r}).write_text(str(p.pid)); time.sleep(30)')
            wall, code, expired, usage = run([sys.executable, '-c', script], folder, 0.3, folder/'log')
            self.assertTrue(expired)
            self.assertNotEqual(code, 0)
            self.assertLess(wall, 3)
            self.assertGreaterEqual(usage['observed_processes'], 2)
            process = psutil.Process(int(pid.read_text())) if psutil.pid_exists(int(pid.read_text())) else None
            if process:
                try:
                    process.wait(timeout=3)
                except psutil.TimeoutExpired:
                    self.assertEqual(process.status(), psutil.STATUS_ZOMBIE)

    def test_normal_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = pathlib.Path(directory)
            _, code, expired, _ = run([sys.executable, '-c', 'print(42)'], folder, 3, folder/'log')
            self.assertEqual(code, 0)
            self.assertFalse(expired)
            self.assertEqual((folder/'log').read_text(), '42\n')

    def test_memory_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = pathlib.Path(directory)
            _, _, expired, usage = run(
                [sys.executable, '-c', 'import time; x=bytearray(64*1024**2); time.sleep(30)'],
                folder, 5, folder/'log', memory_bytes=32*1024**2)
            self.assertTrue(expired)
            self.assertTrue(usage['memory_limit_exceeded'])


if __name__ == '__main__':
    unittest.main()
