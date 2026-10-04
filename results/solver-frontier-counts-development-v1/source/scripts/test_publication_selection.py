import json
import unittest

from select_publication_mcc import ROOT, select


class SelectionTests(unittest.TestCase):
    def test_frozen_selection_is_reproducible_and_disjoint(self):
        previous = json.loads((ROOT/'benchmarks/mcc-selection.json').read_text())
        frozen = json.loads((ROOT/'benchmarks/publication-selection.json').read_text())
        generated = select((ROOT/'vendor/mcc2021/index.html').read_text(), previous)
        self.assertEqual(generated['index_sha256'], frozen['index_sha256'])
        self.assertEqual(generated['models'], [{k: v for k, v in row.items() if k != 'sha256'}
                                                for row in frozen['models']])
        groups = {}
        for split in ('development', 'evaluation'):
            models = [row for row in frozen['models'] if row['split'] == split]
            self.assertEqual(len(models), 16)
            groups[split] = {row['family_group'] for row in models}
            self.assertEqual(len(groups[split]), 8)
        self.assertTrue(groups['development'].isdisjoint(groups['evaluation']))
        self.assertFalse({row['family'] for row in previous['models']} &
                         {row['family'] for row in frozen['models']})

    def test_related_rers_families_share_a_group(self):
        index = '\n'.join(f'INPUTS/{family}-PT-{i}.tgz"'
                          for family in ('RERS17pb101', 'RERS17pb102') for i in range(5))
        rows = select(index, {'models': []})['models']
        self.assertEqual(len(rows), 2)
        self.assertEqual({row['family_group'] for row in rows}, {'RERS'})
        self.assertEqual({row['family'] for row in rows}, {'RERS17pb101'})
        self.assertEqual(select(index, {'models': [{'family': 'RERS19pb999'}]})['models'], [])


if __name__ == '__main__':
    unittest.main()
