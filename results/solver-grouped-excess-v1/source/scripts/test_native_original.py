import hashlib
import json
import pathlib
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from benchmark_smpt_classic import native_original, property_truth
from native_original import translate


NET = '''<pnml><net id="n" type="http://www.pnml.org/version-2009/grammar/ptnet">
<page id="page"><place id="p"><initialMarking><text>1</text></initialMarking></place>
<transition id="t"/><arc id="a" source="p" target="t"/>
</page></net></pnml>'''
ATOM = '<integer-le><tokens-count><place>p</place></tokens-count><integer-constant>0</integer-constant></integer-le>'


def prop(identifier='requested', kind='EF', predicate=ATOM):
    outer, inner = ('exists-path', 'finally') if kind == 'EF' else ('all-paths', 'globally')
    return f'<property><id>{identifier}</id><formula><{outer}><{inner}>{predicate}</{inner}></{outer}></formula></property>'


class NativeOriginalTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = pathlib.Path(self.temporary.name)
        self.net, self.xml = self.folder/'model.pnml', self.folder/'properties.xml'
        self.net.write_text(NET)
        self.binary = self.folder/'fake-backend'
        self.args = SimpleNamespace(binary=self.binary, baseline_binary=self.binary,
                                    native_python=pathlib.Path(sys.executable), seconds=3,
                                    max_states=100, outer_grace=0, track_resources=False)

    def inputs(self, kind='EF', predicate=ATOM, extra=''):
        self.xml.write_text('<property-set>'+extra+prop(kind=kind, predicate=predicate)+'</property-set>')
        problem, selected = translate(self.net, self.xml, 'requested')
        branches = []
        for i, target in enumerate(selected['targets']):
            path = self.folder/f'canonical-{i}.json'
            path.write_text(json.dumps(dict(problem, target=target)))
            branches.append(dict(path=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        return dict(name='query', pnml=self.net.name, xml=self.xml.name,
                    property_id='requested', kind=kind, branches=branches)

    def backend(self, answer=None, code=None):
        if code is None:
            code = 'print('+repr(json.dumps(answer))+')'
        self.binary.write_text('#!'+sys.executable+'\n'+code+'\n')
        self.binary.chmod(0o755)

    def run_query(self, query):
        return native_original(query, self.folder, self.folder, 'fake', 0, self.args)

    def test_exact_id_skips_unrelated_unsupported_property(self):
        query = self.inputs(extra='<property><id>other</id><formula><unsupported/></formula></property>')
        self.backend(dict(verdict='reachable', trace=[0], marking=[0], method='fake'))
        result = self.run_query(query)
        self.assertEqual(result['verdict'], 'reachable')
        self.assertEqual(result['independent_checks'], ['python-witness'])
        self.assertTrue(property_truth(query['kind'], result['verdict']))
        self.assertEqual(result['translation_check'], 'all-canonical-branches-equal')

    def test_ag_counterexample_polarity(self):
        query = self.inputs(kind='AG')
        self.backend(dict(verdict='reachable', trace=[], marking=[1], method='fake'))
        result = self.run_query(query)
        self.assertEqual(result['verdict'], 'reachable')
        self.assertFalse(property_truth(query['kind'], result['verdict']))

    def test_named_native_tool_uses_the_configured_binary_and_engine(self):
        query = self.inputs()
        self.backend(dict(verdict='reachable', trace=[0], marking=[0], method='actual-engine'))
        binary = self.binary
        self.args.binary = self.folder/'missing-default'
        self.args.native_tools = {'fake': dict(binary=str(binary), engine='actual-engine')}
        result = self.run_query(query)
        self.assertEqual(result['verdict'], 'reachable')
        self.assertEqual(result['branches'][0]['engine'], 'actual-engine')
        self.assertIn('actual-engine', result['command'])

    def test_every_disjunct_checked(self):
        predicate = '<disjunction>'+ATOM+ATOM+'</disjunction>'
        query = self.inputs(predicate=predicate)
        self.backend(dict(verdict='unknown', method='fake'))
        result = self.run_query(query)
        self.assertEqual(result['verdict'], 'unknown')
        self.assertEqual([b['branch'] for b in result['branches']], [0, 1])

    def test_false_target_has_no_branches(self):
        query = self.inputs(predicate='<false/>')
        result = self.run_query(query)
        self.assertEqual(result['verdict'], 'unreachable')
        self.assertEqual(result['branches'], [])

    def test_checked_negative(self):
        predicate = '<integer-le><integer-constant>2</integer-constant><tokens-count><place>p</place></tokens-count></integer-le>'
        query = self.inputs(predicate=predicate)
        self.backend(dict(verdict='unreachable', method='fake', reason='finite reachable state space exhausted'))
        result = self.run_query(query)
        self.assertEqual(result['verdict'], 'unreachable')
        self.assertEqual(result['independent_checks'], ['python-finite-closure'])

    def test_unknown_branch_then_witness(self):
        query = self.inputs(predicate='<disjunction>'+ATOM+ATOM+'</disjunction>')
        self.backend(code='import json, sys\n'
                     'answer = {"verdict":"unknown", "method":"fake"}\n'
                     'if "branch-1.json" in sys.argv[2]:\n'
                     '    answer.update(verdict="reachable", trace=[0], marking=[0])\n'
                     'print(json.dumps(answer))')
        result = self.run_query(query)
        self.assertEqual(result['verdict'], 'reachable')
        self.assertEqual([b['verdict'] for b in result['branches']], ['unknown', 'reachable'])

    def test_unchecked_negative_is_unknown(self):
        query = self.inputs()
        self.backend(dict(verdict='unreachable', method='fake'))
        result = self.run_query(query)
        self.assertEqual(result['verdict'], 'unknown')
        self.assertEqual(result['branches'][0]['unchecked_verdict'], 'unreachable')

    def test_false_witness_is_error(self):
        query = self.inputs()
        self.backend(dict(verdict='reachable', trace=[], marking=[1], method='fake'))
        self.assertEqual(self.run_query(query)['verdict'], 'error')

    def test_canonical_translation_mismatch_is_error(self):
        query = self.inputs()
        path = self.folder/query['branches'][0]['path']
        problem = json.loads(path.read_text())
        problem['initial'] = [2]
        path.write_text(json.dumps(problem))
        query['branches'][0]['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.backend(dict(verdict='unknown', method='fake'))
        result = self.run_query(query)
        self.assertEqual(result['verdict'], 'error')
        self.assertIn('disagrees with canonical', result['error'])

    def test_nonzero_backend_exit_is_error(self):
        query = self.inputs()
        self.backend(code='raise SystemExit(2)')
        self.assertEqual(self.run_query(query)['verdict'], 'error')

    def test_invalid_json_is_error(self):
        query = self.inputs()
        self.backend(code='print("bad")')
        self.assertEqual(self.run_query(query)['verdict'], 'error')

    def test_branch_timeout_is_unknown(self):
        query = self.inputs()
        self.backend(code='import time; time.sleep(30)')
        self.args.seconds = 0.15
        self.args.outer_grace = 0.5
        result = self.run_query(query)
        self.assertEqual(result['verdict'], 'unknown')
        self.assertFalse(result['outer_timeout'])
        self.assertTrue(result['branches'][0]['outer_timeout'])

    def test_outer_timeout_does_not_read_partial_proofs(self):
        query = self.inputs()
        with mock.patch('benchmark_smpt_classic.execute', return_value=(3.0, -9, True, {})) as execute:
            result = self.run_query(query)
        self.assertEqual(result['verdict'], 'unknown')
        self.assertEqual(result['independent_checks'], [])
        self.assertEqual(execute.call_args.args[2], self.args.seconds)

    def test_missing_and_duplicate_property_ids_fail(self):
        for body in (prop('other'), prop()+prop()):
            self.xml.write_text('<property-set>'+body+'</property-set>')
            with self.assertRaisesRegex(ValueError, 'exactly once'):
                translate(self.net, self.xml, 'requested')


if __name__ == '__main__':
    unittest.main()
