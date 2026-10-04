"""Schema and original-input composition regressions for the frozen v2 checker."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'results/runner-phase-pair-v2/source/scripts'
sys.path.insert(0, str(RUNNER))
from benchmark import verify, verify_proof
from bounded_validation import run_validation
from native_original import translate
from phase_pair_checker import verify_phase_pair


def fixture():
    problem = dict(places=['p', 'q'], initial=[1, 0],
                   transitions=[dict(name='move', pre=[[0, 1]], post=[[1, 1]])],
                   target=[dict(coefficients=[1, 0], bound=1, equality=False),
                           dict(coefficients=[0, 1], bound=1, equality=False)])
    conflict = dict(left=dict(place=0, constraint=0, negated=False),
                    right=dict(place=1, constraint=1, negated=False))
    proof = dict(kind='phase-pair-closure-v1', groups=[[0, 1]], landmarks=[0],
                 relations=[[[1], [2]], [[1], [2]]], conflicts=[conflict, copy.deepcopy(conflict)])
    return problem, proof


def assign(problem, path, value):
    for key in path[:-1]:
        problem = problem[key]
    problem[path[-1]] = value


class PhasePairSchemaTests(unittest.TestCase):
    def test_complete_schema_and_dispatch(self):
        problem, proof = fixture()
        before = copy.deepcopy(problem)
        self.assertEqual(verify_phase_pair(problem, proof), 'python-phase-pair-closure')
        self.assertEqual(verify_proof(problem, proof), 'python-phase-pair-closure')
        self.assertEqual(verify(problem, dict(verdict='unreachable', proof=proof)), 'python-phase-pair-closure')
        self.assertEqual(problem, before)

    def test_unreferenced_target_regression(self):
        historical = json.loads((ROOT / 'research/phase-pair-schema-v2/prior-acceptance.json').read_text())
        spec = importlib.util.spec_from_file_location('old_phase_pair', ROOT / 'results/runner-phase-pair-v1/source/scripts/phase_pair_checker.py')
        old = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(old)
        self.assertEqual(old.verify_phase_pair(historical['problem'], historical['proof']), historical['old_result'])
        with self.assertRaisesRegex(ValueError, '^invalid target dimension$'):
            verify_phase_pair(historical['problem'], historical['proof'])

    def test_malformed_fields_have_deterministic_errors(self):
        cases = [
            (('places',), 'pq', 'invalid places'),
            (('places', 0), 1, 'invalid places'),
            (('initial',), {'p': 1, 'q': 0}, 'invalid initial marking'),
            (('initial',), [1], 'invalid initial marking'),
            (('initial', 0), True, 'invalid initial marking'),
            (('initial', 0), -1, 'invalid initial marking'),
            (('initial', 0), 2**64, 'invalid initial marking'),
            (('transitions',), {}, 'invalid transitions'),
            (('transitions', 0), None, 'invalid transition fields'),
            (('transitions', 0, 'name'), 7, 'invalid transition name'),
            (('transitions', 0, 'pre'), {}, 'invalid arcs'),
            (('transitions', 0, 'pre'), [[0, 1], [0, 1]], 'duplicate arc place'),
            (('transitions', 0, 'pre', 0), [0], 'invalid weighted arc'),
            (('transitions', 0, 'pre', 0), [0, 0], 'invalid weighted arc'),
            (('transitions', 0, 'pre', 0), [0, 2**64], 'invalid weighted arc'),
            (('transitions', 0, 'pre', 0), [True, 1], 'invalid weighted arc'),
            (('transitions', 0, 'pre', 0), [0, True], 'invalid weighted arc'),
            (('transitions', 0, 'pre', 0), [2, 1], 'invalid weighted arc'),
            (('target',), {}, 'invalid target'),
            (('target', 2), None, 'invalid target fields'),
            (('target', 2, 'coefficients'), '00', 'invalid target dimension'),
            (('target', 2, 'coefficients'), [0], 'invalid target dimension'),
            (('target', 2, 'coefficients', 0), True, 'invalid target arithmetic'),
            (('target', 2, 'coefficients', 0), 2**63, 'invalid target arithmetic'),
            (('target', 2, 'coefficients', 0), -2**63-1, 'invalid target arithmetic'),
            (('target', 2, 'coefficients', 0), 1.0, 'invalid target arithmetic'),
            (('target', 2, 'bound'), True, 'invalid target arithmetic'),
            (('target', 2, 'bound'), 2**63, 'invalid target arithmetic'),
            (('target', 2, 'bound'), -2**63-1, 'invalid target arithmetic'),
            (('target', 2, 'equality'), 0, 'invalid target equality'),
        ]
        for path, value, message in cases:
            with self.subTest(path=path, value=value):
                problem, proof = fixture()
                problem['target'].append(dict(coefficients=[0, 0], bound=0, equality=False))
                assign(problem, path, value)
                with self.assertRaisesRegex(ValueError, '^' + message + '$'):
                    verify_phase_pair(problem, proof)

    def test_missing_fields_and_nonobject_inputs(self):
        for malformed in [None, [], 1, 'problem', {}]:
            with self.subTest(malformed=malformed), self.assertRaisesRegex(ValueError, '^invalid problem fields$'):
                verify_phase_pair(malformed, fixture()[1])
        for fields, message in [((), 'invalid problem fields'), (('transitions', 0), 'invalid transition fields'),
                                (('target', 0), 'invalid target fields')]:
            problem, proof = fixture()
            obj = problem
            for field in fields:
                obj = obj[field]
            for key in list(obj):
                bad = copy.deepcopy(problem)
                obj = bad
                for field in fields:
                    obj = obj[field]
                del obj[key]
                with self.subTest(fields=fields, key=key), self.assertRaisesRegex(ValueError, '^' + message + '$'):
                    verify_phase_pair(bad, proof)

    def test_serde_extra_fields_duplicate_names_and_integer_boundaries(self):
        problem, proof = fixture()
        problem['extra'] = 'allowed'
        problem['places'] = ['same', 'same']
        problem['transitions'][0]['extra'] = None
        problem['transitions'].append(dict(name='move', pre=[[0, 2**64-1]], post=[]))
        problem['target'].append(dict(coefficients=[-2**63, 2**63-1], bound=-2**63,
                                      equality=True, extra='allowed'))
        self.assertEqual(verify_phase_pair(problem, proof), 'python-phase-pair-closure')

    def test_relevance_wrapper_reconstructs_then_checks_phase_pair(self):
        problem, proof = fixture()
        problem['places'].append('irrelevant')
        problem['initial'].append(1)
        problem['transitions'].append(dict(name='unrelated', pre=[[2, 1]], post=[[2, 1]]))
        for row in problem['target']:
            row['coefficients'].append(0)
        wrapper = dict(kind='relevance-v1', places=[0, 1], transitions=[0], inner=proof)
        self.assertEqual(verify_proof(problem, wrapper), 'python-relevance')
        wrapper['inner']['relations'][0][0][0] = 0
        with self.assertRaises(ValueError):
            verify_proof(problem, wrapper)

    def test_bounded_original_input_validation_and_malformed_rejection(self):
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
            problem['target'] = prop['targets'][0]
            problem = json.loads(json.dumps(problem))
            self.assertEqual(problem, fixture()[0])
            artifacts = base/'artifacts'
            artifacts.mkdir()
            canonical = base/'canonical.json'
            metadata = dict(property_id='both', kind='EF', branch_count=1)
            (artifacts/'translation.json').write_text(json.dumps(metadata))
            log = base/'frontend.json'
            log.write_text(json.dumps(dict(metadata, attempts=[dict(branch=0, exit_code=0, outer_timeout=False)])))
            (artifacts/'answer-0.json').write_text(json.dumps(dict(verdict='unreachable', method='phase-pair', proof=fixture()[1])))
            args = SimpleNamespace(native_python=Path(sys.executable), validation_seconds=10,
                                   validation_memory_mib=512, validation_response_mib=1)
            for malformed in [False, True]:
                if malformed:
                    problem['target'].append(dict(coefficients=[0, 0], bound=0, equality='invalid'))
                encoded = json.dumps(problem)
                canonical.write_text(encoded)
                (artifacts/'branch-0.json').write_text(encoded)
                query = dict(property_id='both', kind='EF', branches=[dict(path=canonical.name, sha256=hashlib.sha256(canonical.read_bytes()).hexdigest())])
                result = run_validation(query, base, artifacts, log, 0, args)
                with self.subTest(malformed=malformed):
                    self.assertEqual(result['validation']['exit_code'], 0)
                    self.assertFalse(result['validation']['outer_timeout'])
                    self.assertFalse(result['validation']['included_in_solver_timing'])
                    if malformed:
                        self.assertEqual(result['verdict'], 'error')
                        self.assertEqual(result['error'], 'ValueError: invalid target equality')
                        self.assertEqual(result['independent_checks'], [])
                    else:
                        self.assertEqual(result['verdict'], 'unreachable')
                        self.assertEqual(result['independent_checks'], ['python-phase-pair-closure'])
                        self.assertEqual(result['translation_check'], 'all-canonical-branches-equal')
            canonical.write_text(json.dumps(fixture()[0]))
            query['branches'][0]['sha256'] = hashlib.sha256(canonical.read_bytes()).hexdigest()
            query.update(pnml=net.name, xml=xml.name,
                         pnml_sha256=hashlib.sha256(net.read_bytes()).hexdigest(),
                         xml_sha256=hashlib.sha256(xml.read_bytes()).hexdigest())
            for wrapped in [False, True]:
                proof = fixture()[1]
                if wrapped:
                    proof = dict(kind='relevance-v1', places=[0, 1], transitions=[0], inner=proof)
                outcome = dict(verdict='unreachable', method='phase-pair', proof=proof)
                summary = dict(kind='original-property-v1', property_id='both', property_kind='EF',
                               branch_count=1, verdict='unreachable', property_truth=False,
                               deadline_exceeded=False, parse_seconds=0, solve_seconds=0,
                               attempts=[dict(branch=0, outcome=outcome)])
                log.write_text(json.dumps(summary))
                result = run_validation(query, base, artifacts, log, 0, args, mode='rust-original-v1')
                with self.subTest(rust_original=True, wrapped=wrapped):
                    self.assertEqual(result['verdict'], 'unreachable')
                    self.assertEqual(result['independent_checks'],
                                     ['python-relevance' if wrapped else 'python-phase-pair-closure'])
                    self.assertEqual(result['translation_check'],
                                     'independent-original-input-equals-all-canonical-branches')


if __name__ == '__main__':
    unittest.main(verbosity=2)
