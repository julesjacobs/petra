"""Integration tests for the isolated signed-threshold runner."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'results/runner-threshold-v1/source/scripts'
sys.path.insert(0, str(RUNNER))
from benchmark import verify, verify_proof
from bounded_validation import run_validation
from native_original import translate


def fixture():
    problem = dict(places=['p', 'q'], initial=[1, 0],
                   transitions=[dict(name='move', pre=[[0, 1]], post=[[1, 1]])],
                   target=[dict(coefficients=[1, 0], bound=1, equality=False),
                           dict(coefficients=[0, 1], bound=1, equality=False)])
    def literal(form, threshold):
        return dict(form=form, threshold=str(threshold), negated=True)
    proof = dict(kind='signed-threshold-invariant-v1', forms=[[[0, '1']], [[1, '1']]],
                 clauses=[[literal(0, 1), literal(1, 1)], [literal(0, 2)], [literal(1, 2)]])
    return problem, proof


def wrapped(proof):
    return dict(kind='relevance-v1', places=[0, 1], transitions=[0], inner=proof)


class ThresholdCompositionTests(unittest.TestCase):
    def test_dispatch_and_relevance_composition(self):
        problem, proof = fixture()
        original = copy.deepcopy(problem)
        self.assertEqual(verify_proof(problem, proof), 'python-signed-threshold-invariant')
        self.assertEqual(verify(problem, dict(verdict='unreachable', proof=proof)),
                         'python-signed-threshold-invariant')
        problem['places'].append('unrelated')
        problem['initial'].append(5)
        problem['transitions'].append(dict(name='unrelated', pre=[[2, 1]], post=[[2, 2]]))
        for row in problem['target']:
            row['coefficients'].append(0)
        self.assertEqual(verify_proof(problem, wrapped(proof)), 'python-relevance')
        self.assertEqual(fixture()[0], original)
        proof['clauses'].pop(0)
        with self.assertRaisesRegex(ValueError, 'invariant not inductive'):
            verify_proof(problem, wrapped(proof))

    def test_unreferenced_target_and_malformed_proof_rejected(self):
        problem, proof = fixture()
        problem['target'].append(dict(coefficients=[0], bound=0, equality=False))
        with self.assertRaisesRegex(ValueError, '^invalid target dimension$'):
            verify_proof(problem, proof)
        problem, proof = fixture()
        proof['clauses'][0][0]['threshold'] = 1
        with self.assertRaisesRegex(ValueError, '^expected decimal string$'):
            verify_proof(problem, proof)

    def test_unknown_answers_and_unsupported_proofs_preserve_existing_behavior(self):
        problem, proof = fixture()
        self.assertEqual(verify(problem, dict(verdict='unknown', proof=proof)), 'none')
        proof['kind'] = 'unsupported-future-proof'
        with self.assertRaises(AssertionError):
            verify(problem, dict(verdict='unreachable', proof=proof))

    def test_bounded_rust_original_input_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            net, xml = base/'model.pnml', base/'properties.xml'
            net.write_text('''<pnml><net id="n" type="http://www.pnml.org/version-2009/grammar/ptnet"><page id="page">
<place id="p"><initialMarking><text>1</text></initialMarking></place><place id="q"/>
<transition id="move"/><arc id="a" source="p" target="move"/><arc id="b" source="move" target="q"/>
</page></net></pnml>''')
            atoms = ''.join('<integer-le><integer-constant>1</integer-constant><tokens-count><place>'+p+'</place></tokens-count></integer-le>' for p in ['p', 'q'])
            xml.write_text('<property-set><property><id>both</id><formula><exists-path><finally><conjunction>'+atoms+'</conjunction></finally></exists-path></formula></property></property-set>')
            problem, prop = translate(net, xml, 'both')
            problem = json.loads(json.dumps(dict(problem, target=prop['targets'][0])))
            self.assertEqual(problem, fixture()[0])
            canonical = base/'canonical.json'
            canonical.write_text(json.dumps(problem))
            query = dict(property_id='both', kind='EF', pnml=net.name, xml=xml.name,
                         pnml_sha256=hashlib.sha256(net.read_bytes()).hexdigest(),
                         xml_sha256=hashlib.sha256(xml.read_bytes()).hexdigest(),
                         branches=[dict(path=canonical.name, sha256=hashlib.sha256(canonical.read_bytes()).hexdigest())])
            args = SimpleNamespace(native_python=Path(sys.executable), validation_seconds=10,
                                   validation_memory_mib=512, validation_response_mib=1)
            log = base/'answer.json'
            for variant in ['direct', 'relevance', 'malformed', 'unsupported', 'unknown']:
                proof = fixture()[1]
                if variant == 'relevance':
                    proof = wrapped(proof)
                elif variant == 'malformed':
                    proof['clauses'][0][0]['threshold'] = 1
                elif variant == 'unsupported':
                    proof['kind'] = 'unsupported-future-proof'
                verdict = 'unknown' if variant == 'unknown' else 'unreachable'
                outcome = dict(verdict=verdict, method='supplied-threshold-proof', proof=proof)
                summary = dict(kind='original-property-v1', property_id='both', property_kind='EF',
                               branch_count=1, verdict=verdict, property_truth=None if verdict == 'unknown' else False,
                               deadline_exceeded=False, parse_seconds=0, solve_seconds=0,
                               attempts=[dict(branch=0, outcome=outcome)])
                log.write_text(json.dumps(summary))
                result = run_validation(query, base, base, log, 0, args, mode='rust-original-v1')
                with self.subTest(variant=variant):
                    self.assertEqual(result['validation']['exit_code'], 0)
                    self.assertFalse(result['validation']['outer_timeout'])
                    self.assertFalse(result['validation']['included_in_solver_timing'])
                    if variant == 'malformed':
                        self.assertEqual(result['verdict'], 'error')
                        self.assertEqual(result['error'], 'ValueError: expected decimal string')
                        self.assertEqual(result['independent_checks'], [])
                    elif variant == 'unsupported':
                        self.assertEqual(result['verdict'], 'error')
                        self.assertEqual(result['error'], 'AssertionError: ')
                        self.assertEqual(result['independent_checks'], [])
                    elif variant == 'unknown':
                        self.assertEqual(result['verdict'], 'unknown')
                        self.assertEqual(result['independent_checks'], ['none'])
                        self.assertIsNone(result['property_truth'])
                    else:
                        self.assertEqual(result['verdict'], 'unreachable')
                        self.assertEqual(result['independent_checks'],
                                         ['python-relevance' if variant == 'relevance' else 'python-signed-threshold-invariant'])
                        self.assertFalse(result['property_truth'])
                        self.assertEqual(result['translation_check'],
                                         'independent-original-input-equals-all-canonical-branches')


if __name__ == '__main__':
    unittest.main(verbosity=2)
