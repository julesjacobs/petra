import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from benchmark_smpt_classic import (native, rust_original, configure_original_modes,
                                    method_input_mode, VERIFYPN_MODES)
from native_original import translate
from rust_original_validation import validate
from test_native_original import NET, ATOM, prop

NEGATIVE_ATOM = '<integer-le><integer-constant>2</integer-constant><tokens-count><place>p</place></tokens-count></integer-le>'


class RustOriginalTests(unittest.TestCase):
    def test_buffer_agglomeration_flag_is_scoped_to_selected_original_method(self):
        self.args.methods = ['before', 'after']
        self.args.rust_original_method = []
        self.args.bounded_validation = True
        self.args.buffer_agglomeration_method = ['after']
        configure_original_modes(self.args)
        query = self.inputs()
        for method in self.args.methods:
            with mock.patch('benchmark_smpt_classic.execute', return_value=(4, 0, True, {})) as execute:
                rust_original(query, self.root, self.root, method, 0, self.args)
            self.assertEqual('--buffer-agglomeration' in execute.call_args.args[0], method == 'after')
        for invalid in ['missing', 'smpt-full-portable', 'verifypn-default']:
            self.args.buffer_agglomeration_method = [invalid]
            with self.assertRaises(ValueError):
                configure_original_modes(self.args)
        self.args.buffer_agglomeration_method = ['after']
        self.args.rust_original = False
        self.args.native_original = True
        with self.assertRaises(ValueError):
            configure_original_modes(self.args)

    def test_target_path_potential_flag_is_scoped_to_selected_original_method(self):
        self.args.methods = ['before', 'after']
        self.args.rust_original_method = []
        self.args.bounded_validation = True
        self.args.target_path_potential_method = ['after']
        configure_original_modes(self.args)
        query = self.inputs()
        for method in self.args.methods:
            with mock.patch('benchmark_smpt_classic.execute', return_value=(4, 0, True, {})) as execute:
                rust_original(query, self.root, self.root, method, 0, self.args)
            self.assertEqual('--target-path-potential' in execute.call_args.args[0], method == 'after')
        for invalid in ['missing', 'smpt-full-portable', 'verifypn-default']:
            self.args.target_path_potential_method = [invalid]
            with self.assertRaises(ValueError):
                configure_original_modes(self.args)
        self.args.target_path_potential_method = ['after']
        self.args.rust_original = False
        self.args.native_original = True
        with self.assertRaises(ValueError):
            configure_original_modes(self.args)

    def test_target_zero_trap_flag_is_scoped_to_selected_original_method(self):
        self.args.methods = ['before', 'after']
        self.args.rust_original_method = []
        self.args.bounded_validation = True
        self.args.target_zero_trap_method = ['after']
        configure_original_modes(self.args)
        query = self.inputs()
        for method in self.args.methods:
            with mock.patch('benchmark_smpt_classic.execute', return_value=(4, 0, True, {})) as execute:
                rust_original(query, self.root, self.root, method, 0, self.args)
            self.assertEqual('--target-zero-trap' in execute.call_args.args[0], method == 'after')
        for invalid in ['missing', 'smpt-full-portable', 'verifypn-default']:
            self.args.target_zero_trap_method = [invalid]
            with self.assertRaises(ValueError):
                configure_original_modes(self.args)
        self.args.target_zero_trap_method = ['after']
        self.args.rust_original = False
        self.args.native_original = True
        with self.assertRaises(ValueError):
            configure_original_modes(self.args)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.net = self.root / 'model.pnml'; self.net.write_text(NET)
        self.xml = self.root / 'properties.xml'
        self.log = self.root / 'answer.json'
        self.binary = self.root / 'fake'
        self.args = SimpleNamespace(binary=self.binary, baseline_binary=self.binary, native_original=False,
                                    rust_original=True, native_python=Path(sys.executable), seconds=3,
                                    outer_grace=0, max_states=100, track_resources=False,
                                    validation_seconds=3, validation_memory_mib=512, validation_response_mib=1)

    def inputs(self, kind='EF', predicate=ATOM, extra=''):
        self.xml.write_text('<property-set>'+extra+prop(kind=kind, predicate=predicate)+'</property-set>')
        net, selected = translate(self.net, self.xml, 'requested')
        branches = []
        for i, target in enumerate(selected['targets']):
            path = self.root / f'branch-{i}.json'
            path.write_text(json.dumps(dict(net, target=target)))
            branches.append(dict(path=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        return dict(name='query', property_id='requested', kind=kind, branches=branches,
                    pnml=self.net.name, xml=self.xml.name,
                    pnml_sha256=hashlib.sha256(self.net.read_bytes()).hexdigest(),
                    xml_sha256=hashlib.sha256(self.xml.read_bytes()).hexdigest())

    def outcome(self, verdict='reachable', **changes):
        result = dict(verdict=verdict, method='fake', trace=[0], marking=[0])
        result.update(changes)
        return result

    def summary(self, query, outcomes, verdict=None, deadline=False):
        if verdict is None:
            verdict = ('unknown' if deadline else 'reachable' if any(a['verdict'] == 'reachable' for a in outcomes)
                       else 'unreachable' if len(outcomes) == len(query['branches']) and all(a['verdict'] == 'unreachable' for a in outcomes)
                       else 'unknown')
        return dict(kind='original-property-v1', property_id='requested', property_kind=query['kind'],
                    branch_count=len(query['branches']), verdict=verdict,
                    property_truth=None if verdict == 'unknown' else (verdict == 'reachable') == (query['kind'] == 'EF'),
                    deadline_exceeded=deadline, reason='test', parse_seconds=0.001, solve_seconds=0.001,
                    attempts=[dict(branch=i, outcome=answer) for i, answer in enumerate(outcomes)])

    def check(self, query, summary, outer_timeout=False, **limits):
        self.log.write_text(json.dumps(summary))
        return validate(dict(query=query, corpus=str(self.root), log=str(self.log), exit_code=0,
                             response_bytes=1024**2, outer_timeout=outer_timeout, **limits))

    def test_configurable_dag_checker_budget_reaches_rust_frontend_validation(self):
        query = self.inputs(predicate=NEGATIVE_ATOM)
        answer = self.outcome('unreachable', proof=dict(kind='dag-cnf-rup-v1', control_places=[0], additions=[[]]))
        with mock.patch('dag_checker.verify', return_value='python-dag-cnf-rup') as checker:
            result = self.check(query, self.summary(query, [answer]), dag_check_max_work=91_000_000)
        self.assertEqual(result['verdict'], 'unreachable')
        self.assertEqual(checker.call_args.kwargs['max_work'], 91_000_000)
        with mock.patch('dag_checker.verify', side_effect=TimeoutError('DAG verification work limit')):
            with self.assertRaises(TimeoutError):
                self.check(query, self.summary(query, [answer]), dag_check_max_work=1)

    def test_original_positive_and_exact_id(self):
        query = self.inputs(extra='<property><id>unrelated</id><formula><unsupported/></formula></property>')
        result = self.check(query, self.summary(query, [self.outcome()]))
        self.assertEqual(result['verdict'], 'reachable')
        self.assertEqual(result['independent_checks'], ['python-witness'])

    def test_ag_counterexample_truth(self):
        query = self.inputs(kind='AG')
        result = self.check(query, self.summary(query, [self.outcome(trace=[], marking=[1])]))
        self.assertEqual(result['verdict'], 'reachable')
        self.assertIs(result['property_truth'], False)

    def test_zero_branches_and_empty_conjunction(self):
        for kind, predicate, verdict in [('EF', '<false/>', 'unreachable'), ('AG', '<true/>', 'unreachable'),
                                          ('EF', '<true/>', 'reachable')]:
            query = self.inputs(kind, predicate)
            outcomes = [self.outcome(trace=[], marking=[1])] if verdict == 'reachable' else []
            result = self.check(query, self.summary(query, outcomes))
            self.assertEqual(result['verdict'], verdict)

    def test_meaningful_threshold_and_farkas_negative_certificates(self):
        query = self.inputs(predicate=NEGATIVE_ATOM)
        answers = [self.outcome('unreachable', proof=dict(kind='threshold-closure-v1', thresholds=[2], states=[[1], [0]])),
                   self.outcome('unreachable', certificate=['1', '0', '1'])]
        for answer in answers:
            result = self.check(query, self.summary(query, [answer]))
            self.assertEqual(result['verdict'], 'unreachable')
            self.assertTrue(result['independent_checks'][0].startswith('python-'))

    def test_unknown_then_positive_and_partial_negative(self):
        query = self.inputs(predicate='<disjunction>'+ATOM+ATOM+'</disjunction>')
        result = self.check(query, self.summary(query, [self.outcome('unknown'), self.outcome()]))
        self.assertEqual(result['verdict'], 'reachable')
        query = self.inputs(predicate='<disjunction>'+NEGATIVE_ATOM+NEGATIVE_ATOM+'</disjunction>')
        negative = self.outcome('unreachable', certificate=['1', '0', '1'])
        result = self.check(query, self.summary(query, [negative]))
        self.assertEqual(result['verdict'], 'unknown')
        with self.assertRaisesRegex(ValueError, 'aggregate verdict'):
            self.check(query, self.summary(query, [negative], verdict='unreachable'))

    def test_unchecked_negative_is_unknown(self):
        query = self.inputs(predicate=NEGATIVE_ATOM)
        result = self.check(query, self.summary(query, [self.outcome('unreachable')]))
        self.assertEqual(result['verdict'], 'unknown')
        self.assertIsNone(result['property_truth'])

    def test_forged_identity_polarity_count_truth_and_branch_prefix(self):
        query = self.inputs()
        good = self.summary(query, [self.outcome()])
        for field, value in [('property_id', 'other'), ('property_kind', 'AG'), ('branch_count', 2),
                             ('branch_count', True), ('property_truth', 1), ('property_truth', False),
                             ('verdict', 'unreachable'), ('deadline_exceeded', 0)]:
            bad = copy.deepcopy(good); bad[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.check(query, bad)
        for index in [1, True, -1]:
            bad = copy.deepcopy(good); bad['attempts'][0]['branch'] = index
            with self.subTest(index=index), self.assertRaises(ValueError):
                self.check(query, bad)

    def test_forged_witness_and_negative_certificate_rejected(self):
        query = self.inputs()
        with self.assertRaises(AssertionError):
            self.check(query, self.summary(query, [self.outcome(trace=[], marking=[1])]))
        query = self.inputs(predicate=NEGATIVE_ATOM)
        with self.assertRaises(AssertionError):
            self.check(query, self.summary(query, [self.outcome('unreachable', certificate=['0', '0', '0'])]))

    def test_deadline_unknown_is_never_upgraded(self):
        query = self.inputs(predicate=NEGATIVE_ATOM)
        summary = self.summary(query, [self.outcome('unreachable', certificate=['1', '0', '1'])], deadline=True)
        result = self.check(query, summary)
        self.assertEqual(result['verdict'], 'unknown')
        self.assertIsNone(result['property_truth'])
        self.assertTrue(result['deadline_exceeded'])
        result = self.check(query, {}, outer_timeout=True)
        self.assertEqual(result['verdict'], 'unknown')
        self.assertEqual(result['independent_checks'], [])

    def test_canonical_and_original_source_mutations_rejected(self):
        query = self.inputs()
        path = self.root / query['branches'][0]['path']
        problem = json.loads(path.read_text()); problem['initial'] = [2]
        path.write_text(json.dumps(problem))
        query['branches'][0]['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, 'canonical branch'):
            self.check(query, self.summary(query, [self.outcome()]))
        query = self.inputs()
        self.net.write_text(NET.replace('<text>1</text>', '<text>2</text>'))
        with self.assertRaisesRegex(ValueError, 'checksum'):
            self.check(query, self.summary(query, [self.outcome()]))

    def test_opt_in_adapter_uses_bounded_validation(self):
        query = self.inputs()
        summary = self.summary(query, [self.outcome()])
        self.binary.write_text('#!'+sys.executable+'\nprint('+repr(json.dumps(summary))+')\n')
        self.binary.chmod(0o755)
        result = native(query, self.root, self.root, 'fake', 0, self.args)
        self.assertEqual(result['verdict'], 'reachable', result)
        self.assertIn('--pnml', result['command'])
        self.assertEqual(result['input_mode'], 'rust-original-v1')
        self.assertFalse(result['validation']['included_in_solver_timing'])

    def test_adapter_discards_outer_timeout_or_late_success_before_validation(self):
        query = self.inputs()
        for wall, expired in [(3.1, False), (2, True)]:
            with mock.patch('benchmark_smpt_classic.execute', return_value=(wall, 0, expired, {})), \
                    mock.patch('bounded_validation.run_validation') as checker:
                result = rust_original(query, self.root, self.root, 'fake', 0, self.args)
            self.assertEqual(result['verdict'], 'unknown')
            checker.assert_not_called()

    def test_mixed_frontends_share_binary_and_keep_independent_validation(self):
        query = self.inputs()
        summary = self.summary(query, [self.outcome()])
        self.binary.write_text('#!'+sys.executable+'\nimport sys\nprint('
                               +repr(json.dumps(summary))+' if "--pnml" in sys.argv else '
                               +repr(json.dumps(self.outcome()))+')\n')
        self.binary.chmod(0o755)
        self.args.rust_original = False
        self.args.rust_original_method = ['candidate-rust']
        self.args.native_original = True
        external = next(iter(VERIFYPN_MODES))
        self.args.methods = ['candidate-python', 'candidate-rust', external]
        self.args.native_tools = {label: dict(binary=str(self.binary), engine='fake')
                                  for label in self.args.methods[:2]}
        configure_original_modes(self.args)
        results = {label: native(query, self.root, self.root, label, 0, self.args)
                   for label in self.args.methods[:2]}
        for label, result in results.items():
            self.assertEqual(result['verdict'], 'reachable', (label, result))
            self.assertEqual(result['independent_checks'], ['python-witness'])
            self.assertFalse(result['validation']['included_in_solver_timing'])
        self.assertEqual(results['candidate-rust']['command'][0], str(self.binary))
        self.assertEqual(results['candidate-python']['command'][0], str(self.args.native_python))
        self.assertEqual(method_input_mode('candidate-rust', self.args), 'rust-original-v1')
        self.assertEqual(method_input_mode('candidate-python', self.args), 'python-original-v1')
        self.assertEqual(method_input_mode(external, self.args), 'verifypn-original')

    def test_method_selection_validation_and_legacy_defaults(self):
        self.args.methods = ['one', 'two', 'smpt', next(iter(VERIFYPN_MODES))]
        self.args.rust_original = False
        self.args.rust_original_method = []
        self.args.bounded_validation = False
        configure_original_modes(self.args)
        self.assertEqual(method_input_mode('one', self.args), 'canonical-json')
        self.args.native_original = True
        configure_original_modes(self.args)
        self.assertEqual(method_input_mode('one', self.args), 'python-original-v1')
        self.args.rust_original_method = ['one', 'two']
        configure_original_modes(self.args)
        self.assertTrue(self.args.bounded_validation)
        self.assertEqual(method_input_mode('two', self.args), 'rust-original-v1')
        for invalid in ['absent', 'smpt', self.args.methods[-1]]:
            self.args.rust_original_method = [invalid]
            with self.assertRaisesRegex(ValueError, 'selected native method'):
                configure_original_modes(self.args)
        self.args.rust_original_method = []
        self.args.rust_original = True
        with self.assertRaisesRegex(ValueError, 'distinct input modes'):
            configure_original_modes(self.args)
        self.args.native_original = False
        configure_original_modes(self.args)
        self.assertEqual(method_input_mode('two', self.args), 'rust-original-v1')


if __name__ == '__main__':
    unittest.main()
