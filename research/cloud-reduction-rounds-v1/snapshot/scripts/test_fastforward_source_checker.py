import copy
import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest

from fastforward_source_checker import Budget, Formula, check_artifact, parse_lola, replay

SOURCE = '''PLACE x,y,z; MARKING x:2;
TRANSITION read
CONSUME x:2;
PRODUCE x:2,y:3;
TRANSITION finish
CONSUME x:2,y:3;
PRODUCE z:1;
TRANSITION zero
CONSUME z:0;
PRODUCE x:0;
'''
MAPPING = {'places': ['z', 'x', 'y'], 'transitions': ['finish', 'zero', 'read']}
CANONICAL = {'places': ['p0', 'p1', 'p2'], 'initial': [0, 2, 0], 'target': [], 'transitions': [
    {'name': 't0', 'pre': [[1, 2], [2, 3]], 'post': [[0, 1]]},
    {'name': 't1', 'pre': [], 'post': []},
    {'name': 't2', 'pre': [[1, 2]], 'post': [[1, 2], [2, 3]]}]}
OUTCOME = {'verdict': 'reachable', 'trace': [2, 0], 'marking': [1, 0, 0]}
FORMULA = 'EF ((z=1 AND x=0 AND y=0) OR z>=2)'


class SourceReplayTests(unittest.TestCase):
    def test_weighted_read_arcs_permuted_mapping_and_exact_zero(self):
        result = replay(SOURCE, FORMULA, MAPPING, CANONICAL, OUTCOME)
        self.assertEqual(result['verdict'], 'reachable')
        self.assertEqual(result['marking'], [1, 0, 0])
        self.assertEqual(result['independent_check'], 'python-original-lola-witness')

    def test_source_target_overrules_weakened_canonical_target(self):
        proposal = {'verdict': 'reachable', 'trace': [2], 'marking': [0, 2, 3]}
        with self.assertRaisesRegex(ValueError, 'source formula rejects'):
            replay(SOURCE, 'EF (y>=3 AND x=0)', MAPPING, CANONICAL, proposal)
        proposal = {'verdict': 'reachable', 'trace': [], 'marking': [0, 2, 0]}
        self.assertEqual(replay(SOURCE, 'EF (x=2 AND y=0 AND z=0)', MAPPING, CANONICAL, proposal)['steps'], 0)

    def test_mapping_must_be_bijective_and_match_full_canonical_net(self):
        for bad in [dict(MAPPING, places=['z', 'x', 'x']), dict(MAPPING, transitions=['finish', 'zero']),
                    dict(MAPPING, places=['z', 'x', 'absent']), dict(MAPPING, transitions=['read', 'zero', 'finish'])]:
            with self.subTest(mapping=bad), self.assertRaises(ValueError):
                replay(SOURCE, FORMULA, bad, CANONICAL, OUTCOME)
        mutations = [lambda p: p['initial'].__setitem__(1, 3),
                     lambda p: p['transitions'][2]['pre'][0].__setitem__(1, 1),
                     lambda p: p['transitions'][0]['post'].append([0, 1]),
                     lambda p: p['transitions'][0].__setitem__('name', 'wrong'),
                     lambda p: p['transitions'][1]['pre'].append([0, 1])]
        for change in mutations:
            bad = copy.deepcopy(CANONICAL)
            change(bad)
            with self.subTest(canonical=bad), self.assertRaises(ValueError):
                replay(SOURCE, FORMULA, MAPPING, bad, OUTCOME)

    def test_disabled_invalid_and_forged_witnesses(self):
        for trace in [[0], [2, 0, 0], [-1], [3], [True], ['2']]:
            bad = dict(OUTCOME, trace=trace, marking=None)
            with self.subTest(trace=trace), self.assertRaises(ValueError):
                replay(SOURCE, FORMULA, MAPPING, CANONICAL, bad)
        for marking in [[1, 0, 1], [True, 0, 0], [-1, 0, 0]]:
            with self.subTest(marking=marking), self.assertRaises(ValueError):
                replay(SOURCE, FORMULA, MAPPING, CANONICAL, dict(OUTCOME, marking=marking))
        with self.assertRaises(ValueError):
            replay(SOURCE, FORMULA, MAPPING, CANONICAL, dict(OUTCOME, verdict='unreachable'))

    def test_arbitrary_precision_replay(self):
        huge = 2**80
        source = f'PLACE p; MARKING p:{huge};\nTRANSITION inc\nCONSUME p:{huge};\nPRODUCE p:{huge+1};'
        canonical = {'places': ['p0'], 'initial': [huge], 'target': [], 'transitions': [
            {'name': 't0', 'pre': [[0, huge]], 'post': [[0, huge+1]]}]}
        answer = {'verdict': 'reachable', 'trace': [0, 0], 'marking': [huge+2]}
        result = replay(source, f'EF (p={huge+2})', {'places': ['p'], 'transitions': ['inc']}, canonical, answer)
        self.assertEqual(result['marking'], [huge+2])

    def test_scope_and_malformed_source_rejection(self):
        for text in ['EF (x=2) AND y=0', 'AG (x=2)', 'EF (x< =2)', 'EF (x=2) garbage', 'EF x=2', 'EF (unknown=0)']:
            with self.subTest(formula=text), self.assertRaises(ValueError):
                Formula(text, ['x', 'y'], Budget())
        for source in [SOURCE.replace('x,y,z', 'x,,z'), SOURCE.replace('x:2;', 'x:2,x:1;', 1),
                       SOURCE + 'garbage', SOURCE.replace('CONSUME x:2;', 'CONSUME x:-2;'),
                       SOURCE.replace('TRANSITION zero', 'TRANSITION read')]:
            with self.subTest(source=source), self.assertRaises(ValueError):
                parse_lola(source, Budget())

    def test_resource_limits(self):
        with self.assertRaises(TimeoutError):
            replay(SOURCE, FORMULA, MAPPING, CANONICAL, OUTCOME, max_work=0)
        with self.assertRaises(TimeoutError):
            replay(SOURCE, FORMULA, MAPPING, CANONICAL, OUTCOME, deadline=time.monotonic()-1)

    def test_hashed_artifact_and_original_property_wrapper(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus, source = root / 'corpus', root / 'source'
            corpus.mkdir(); (source / 'upstream').mkdir(parents=True)
            def write(path, data):
                path.write_bytes(data)
                return hashlib.sha256(data).hexdigest()
            lola_hash = write(source / 'upstream/model.lola', SOURCE.encode())
            formula_hash = write(source / 'upstream/model.formula', FORMULA.encode())
            acquisition_hash = write(source / 'acquisition.json', json.dumps({'files': [
                {'path': 'model.lola', 'sha256': lola_hash}, {'path': 'model.formula', 'sha256': formula_hash}]}).encode())
            canonical_hash = write(corpus / 'branch.json', json.dumps(CANONICAL).encode())
            mapping_hash = write(corpus / 'mapping.json', json.dumps(MAPPING).encode())
            row = {'name': 'example', 'status': 'imported', 'kind': 'EF', 'property_id': 'reachability',
                   'source_lola': 'model.lola', 'source_lola_sha256': lola_hash,
                   'source_formula': 'model.formula', 'source_formula_sha256': formula_hash,
                   'source_mapping': 'mapping.json', 'source_mapping_sha256': mapping_hash,
                   'branches': [{'path': 'branch.json', 'sha256': canonical_hash}]}
            write(corpus / 'manifest.json', json.dumps({'acquisition_sha256': acquisition_hash, 'queries': [row]}).encode())
            wrapped = {'kind': 'original-property-v1', 'property_id': 'reachability', 'property_kind': 'EF',
                       'branch_count': 1, 'verdict': 'reachable', 'property_truth': True, 'deadline_exceeded': False,
                       'attempts': [{'branch': 0, 'outcome': OUTCOME}]}
            answer = root / 'answer.json'; answer.write_text(json.dumps(wrapped))
            request = {'corpus': str(corpus), 'source': str(source), 'query': 'example', 'answer': str(answer)}
            self.assertEqual(check_artifact(request)['verdict'], 'reachable')
            (source / 'upstream/model.formula').write_text('EF (z>=0)')
            with self.assertRaisesRegex(ValueError, 'SHA256'):
                check_artifact(request)


if __name__ == '__main__':
    unittest.main()
