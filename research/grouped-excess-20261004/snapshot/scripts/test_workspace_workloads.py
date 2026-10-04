import pathlib
import unittest
from unittest.mock import Mock, patch

import process_runner


class WorkspaceWorkloadTests(unittest.TestCase):
    def test_inaccessible_process_does_not_hide_following_workspace_workload(self):
        root = pathlib.Path('/tmp/pvass-workload-test').resolve()
        for exception in (SystemError('sysctl failed'), PermissionError('denied'),
                          process_runner.psutil.NoSuchProcess(1)):
            for attribute in ('name', 'cmdline', 'cwd'):
                inaccessible = Mock()
                inaccessible.name.return_value = 'cargo'
                inaccessible.cmdline.return_value = ['cargo', 'build']
                getattr(inaccessible, attribute).side_effect = exception
                cargo = Mock(pid=23)
                cargo.name.return_value = 'cargo'
                cargo.cmdline.return_value = ['cargo', 'test']
                cargo.cwd.return_value = str(root / 'subdir')
                cargo.create_time.return_value = 42
                cargo.status.return_value = 'running'
                with self.subTest(exception=exception, attribute=attribute), patch.object(
                        process_runner.psutil, 'process_iter', return_value=iter([inaccessible, cargo])):
                    self.assertEqual(process_runner.workspace_workloads(root),
                                     [dict(pid=23, created=42, name='cargo')])

    def test_unrelated_and_zombie_processes_remain_excluded(self):
        root = pathlib.Path('/tmp/pvass-workload-test').resolve()
        other = Mock()
        other.name.return_value = 'cargo'
        other.cmdline.return_value = ['cargo', 'build']
        other.cwd.return_value = '/tmp/other-workspace'
        other.status.return_value = 'running'
        zombie = Mock()
        zombie.name.return_value = 'vass-reach'
        zombie.cmdline.return_value = ['vass-reach']
        zombie.status.return_value = process_runner.psutil.STATUS_ZOMBIE
        smpt = Mock(pid=24)
        smpt.name.return_value = 'python'
        smpt.cmdline.return_value = ['python', '-m', 'smpt']
        smpt.cwd.return_value = str(root)
        smpt.create_time.return_value = 43
        smpt.status.return_value = 'running'
        with patch.object(process_runner.psutil, 'process_iter', return_value=iter([other, zombie, smpt])):
            self.assertEqual(process_runner.workspace_workloads(root),
                             [dict(pid=24, created=43, name='python')])


if __name__ == '__main__':
    unittest.main()
