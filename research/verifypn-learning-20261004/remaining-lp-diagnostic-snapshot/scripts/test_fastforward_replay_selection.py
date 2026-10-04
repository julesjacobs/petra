import copy
import hashlib
from pathlib import Path
import tempfile
import unittest

from replay_fastforward_results import check_source_query


class SourceQueryIdentityTests(unittest.TestCase):
    def setUp(self):
        self.original_root = Path('/artifact/import')
        self.measured_root = Path('/artifact/selection')
        self.original = dict(name='query', kind='EF', property_id='reachability',
                             source_lola='input.lola', source_formula='input.formula',
                             source_lola_sha256='lola', source_formula_sha256='formula',
                             source_mapping_sha256='mapping', pnml_sha256='pnml',
                             xml_sha256='xml', source_mapping='q/map.json',
                             pnml='q/model.pnml', xml='q/query.xml',
                             branches=[dict(path='q/0.json', sha256='zero'),
                                       dict(path='q/1.json', sha256='one')])
        self.measured = copy.deepcopy(self.original)
        for key in ('source_mapping', 'pnml', 'xml'):
            self.measured[key] = '../import/' + self.measured[key]
        for branch in self.measured['branches']:
            branch['path'] = '../import/' + branch['path']

    def check(self):
        check_source_query(self.measured, self.original, self.measured_root, self.original_root)

    def test_derived_paths_resolve_to_same_inputs(self):
        self.check()

    def test_changed_identity_rejected(self):
        for key in ('kind', 'property_id', 'source_lola_sha256', 'source_formula_sha256',
                    'source_mapping_sha256', 'pnml_sha256', 'xml_sha256'):
            with self.subTest(key=key):
                original = self.measured[key]
                self.measured[key] = 'changed'
                with self.assertRaises(ValueError):
                    self.check()
                self.measured[key] = original

    def test_branch_order_rejected(self):
        self.measured['branches'].reverse()
        with self.assertRaises(ValueError):
            self.check()

    def test_branch_path_rejected_even_with_matching_hash(self):
        self.measured['branches'][0]['path'] = 'other.json'
        with self.assertRaises(ValueError):
            self.check()

    def test_mapping_path_rejected_even_with_matching_hash(self):
        self.measured['source_mapping'] = 'other.json'
        with self.assertRaises(ValueError):
            self.check()

    def test_unrebased_missing_mapping_requires_opt_in_and_verified_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            self.original_root = Path(directory) / 'import'
            self.measured_root = Path(directory) / 'selection'
            path = self.original_root / self.original['source_mapping']
            path.parent.mkdir(parents=True)
            path.write_bytes(b'pinned source mapping')
            pinned = hashlib.sha256(path.read_bytes()).hexdigest()
            self.original['source_mapping_sha256'] = pinned
            self.measured['source_mapping_sha256'] = pinned
            self.measured['source_mapping'] = self.original['source_mapping']
            with self.assertRaises(ValueError):
                self.check()
            check = lambda: check_source_query(
                self.measured, self.original, self.measured_root, self.original_root,
                allow_unrebased_mapping=True)
            exceptions = check()
            self.assertEqual(len(exceptions), 1)
            self.assertEqual(exceptions[0]['sha256'], pinned)
            self.assertEqual(exceptions[0]['query'], 'query')
            self.assertEqual(exceptions[0]['verified_source_path'], str(path))
            path.write_bytes(b'changed')
            with self.assertRaises(ValueError):
                check()
            path.write_bytes(b'pinned source mapping')
            self.measured['source_mapping'] = 'other.json'
            with self.assertRaises(ValueError):
                check()
            self.measured['source_mapping'] = self.original['source_mapping']
            measured_path = self.measured_root / self.measured['source_mapping']
            measured_path.parent.mkdir(parents=True)
            measured_path.write_bytes(b'pinned source mapping')
            with self.assertRaises(ValueError):
                check()
            measured_path.unlink()
            measured_path.symlink_to('missing-file')
            with self.assertRaises(ValueError):
                check()
            measured_path.unlink()
            self.measured['pnml'] = 'other.pnml'
            with self.assertRaises(ValueError):
                check()


if __name__ == '__main__':
    unittest.main()
