import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bounded_validation import InputChecks, validate, run_validation
from benchmark_smpt_classic import import_failure, preflight_inputs
from test_native_original import NativeOriginalTests


class BoundedNativeTests(NativeOriginalTests):
    def setUp(self):
        super().setUp()
        self.args.bounded_validation = True
        self.args.validation_seconds = 3
        self.args.validation_memory_mib = 512
        self.args.validation_response_mib = 1

    def test_validation_timeout_downgrades_and_keeps_solver_timing(self):
        query = self.inputs()
        self.backend(dict(verdict='reachable', trace=[0], marking=[0], method='fake'))
        with patch('process_runner.run', return_value=(3.0, -9, True, {})):
            result = self.run_query(query)
        self.assertEqual(result['verdict'], 'unknown')
        self.assertEqual(result['validation_failure'], 'timeout')
        self.assertFalse(result['validation']['included_in_solver_timing'])
        self.assertGreater(result['wall_seconds'], 0)
        self.assertLess(result['wall_seconds'], 3)

    def test_validation_memory_failure_is_unknown(self):
        query = self.inputs()
        with patch('process_runner.run', return_value=(1, -9, True, {'memory_limit_exceeded': True})):
            result = run_validation(query, self.folder, self.folder, self.folder/'log', 0, self.args)
        self.assertEqual(result['verdict'], 'unknown')
        self.assertEqual(result['validation_failure'], 'memory-limit')


class PreflightTests(unittest.TestCase):
    def test_streaming_deduplication_and_mutation_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'input'
            data = b'a'*(1024*1024+17)
            path.write_bytes(data)
            digest = hashlib.sha256(data).hexdigest()
            checks = InputChecks()
            with patch.object(Path, 'read_bytes', side_effect=AssertionError('whole-file read')):
                checks.check(path, digest)
                checks.check(path, digest)
            self.assertEqual(checks.bytes_hashed, len(data))
            self.assertEqual(len(checks.seen), 1)
            path.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'changed'):
                checks.unchanged()

    def test_failed_slots_never_require_absent_files(self):
        query = dict(name='slot', status='unsupported', observed=False, property_slot=0, error='timeout')
        inputs = preflight_inputs([query], Path('/absent'), True)
        self.assertEqual(len(inputs.seen), 0)
        result = import_failure(query)
        self.assertEqual(result['verdict'], 'unsupported')
        self.assertFalse(result['execution_attempted'])
        self.assertIsNone(result['resources'])
        self.assertEqual(result['failure_stage'], 'collection')
        self.assertNotIn('property_id', result)


if __name__ == '__main__':
    unittest.main()
