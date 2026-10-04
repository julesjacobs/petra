import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from benchmark import DEFAULT_DAG_CHECK_WORK, verify
from benchmark_smpt_classic import native
from bounded_validation import run_validation, validate, validation_result


class DagValidationLimitsTests(unittest.TestCase):
    def setUp(self):
        self.problem = dict(places=['control'], initial=[1], transitions=[],
                            target=[dict(coefficients=[1], bound=2, equality=False)])
        self.answer = dict(verdict='unreachable', method='dag-sat',
                           proof=dict(kind='dag-cnf-rup-v1', control_places=[0], additions=[[]]))
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        path = self.root / 'branch-0.json'
        path.write_text(json.dumps(self.problem))
        query = dict(property_id='property', kind='EF', branches=[dict(path=path.name,
                     sha256=hashlib.sha256(path.read_bytes()).hexdigest())])
        identity = dict(property_id='property', kind='EF', branch_count=1)
        (self.root / 'translation.json').write_text(json.dumps(identity))
        (self.root / 'answer-0.json').write_text(json.dumps(self.answer))
        self.log = self.root / 'frontend.json'
        self.log.write_text(json.dumps(dict(identity, attempts=[dict(branch=0, outer_timeout=False, exit_code=0)])))
        self.request = dict(query=query, corpus=str(self.root), artifacts=str(self.root), log=str(self.log),
                            exit_code=0, memory_bytes=512*1024**2, response_bytes=1024**2)

    def test_default_and_explicit_work_limit_reach_dag_checker(self):
        with patch('dag_checker.verify', return_value='python-dag-cnf-rup') as checker:
            verify(self.problem, self.answer)
            self.assertEqual(checker.call_args.kwargs['max_work'], DEFAULT_DAG_CHECK_WORK)
            verify(self.problem, self.answer, dag_max_work=77_000_000)
            self.assertEqual(checker.call_args.kwargs['max_work'], 77_000_000)
        self.assertEqual(verify(self.problem, self.answer), 'python-dag-cnf-rup')
        with self.assertRaises(TimeoutError):
            verify(self.problem, self.answer, dag_max_work=1)

    def test_bounded_python_frontend_budget_and_resource_classification(self):
        self.request['dag_check_max_work'] = 1
        result = validation_result(self.request)
        self.assertEqual(result['verdict'], 'unknown')
        self.assertEqual(result['validation_failure'], 'checker-resource-limit')
        self.assertIn('work limit', result['validation_reason'])
        self.assertNotIn('error', result)
        self.request['dag_check_max_work'] = 1_000_000
        self.assertEqual(validation_result(self.request)['verdict'], 'unreachable')
        with patch('dag_checker.verify', return_value='python-dag-cnf-rup') as checker:
            validate(self.request)
            self.assertEqual(checker.call_args.kwargs['max_work'], 1_000_000)

    def test_checker_deadline_and_malformed_proofs_are_distinguished(self):
        with patch('bounded_validation.validate', side_effect=TimeoutError('DAG verification deadline')):
            result = validation_result(self.request)
        self.assertEqual(result['verdict'], 'unknown')
        self.assertEqual(result['validation_failure'], 'checker-resource-limit')
        self.answer['proof']['additions'] = [[2], []]
        (self.root / 'answer-0.json').write_text(json.dumps(self.answer))
        result = validation_result(self.request)
        self.assertEqual(result['verdict'], 'error')
        self.assertIn('invalid RUP literal', result['error'])
        self.assertNotIn('validation_failure', result)

    def test_canonical_backend_reports_resource_exhaustion_as_unknown(self):
        args = SimpleNamespace(native_original=False, binary=Path('/unused'), seconds=3,
                               outer_grace=0, max_states=100, validation_dag_work=1)
        query = dict(self.request['query'], name='query')

        def run(command, cwd, seconds, output, args):
            output.write_text(json.dumps(self.answer))
            return 0.01, 0, False, {}

        with patch('benchmark_smpt_classic.execute', side_effect=run):
            result = native(query, self.root, self.root, 'dag-sat', 0, args)
        self.assertEqual(result['verdict'], 'unknown')
        self.assertEqual(result['branches'][0]['validation_failure'], 'checker-resource-limit')
        self.assertNotIn('error', result['branches'][0])
        args.validation_dag_work = 1_000_000
        self.answer['proof']['additions'] = [[2], []]
        with patch('benchmark_smpt_classic.execute', side_effect=run):
            result = native(query, self.root, self.root, 'dag-sat', 0, args)
        self.assertEqual(result['verdict'], 'error')

    def test_worker_request_report_and_actual_low_budget_response(self):
        args = SimpleNamespace(native_python=Path(sys.executable), validation_seconds=3,
                               validation_memory_mib=512, validation_response_mib=1, validation_dag_work=1)
        result = run_validation(self.request['query'], self.root, self.root, self.log, 0, args)
        self.assertEqual(result['verdict'], 'unknown', result)
        self.assertEqual(result['validation_failure'], 'checker-resource-limit')
        self.assertEqual(result['validation']['dag_check_max_work'], 1)
        self.assertFalse(result['validation']['included_in_solver_timing'])
        request = json.loads(self.log.with_name(self.log.name + '.validation-request.json').read_text())
        self.assertEqual(request['dag_check_max_work'], 1)
        del args.validation_dag_work
        with patch('process_runner.run', return_value=(1, -9, True, {})):
            result = run_validation(self.request['query'], self.root, self.root, self.log, 0, args)
        self.assertEqual(result['validation']['dag_check_max_work'], DEFAULT_DAG_CHECK_WORK)


if __name__ == '__main__':
    unittest.main()
