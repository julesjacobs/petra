import json
import unittest

from select_stress_mcc import ROOT, select


class SelectionTests(unittest.TestCase):
    def test_frozen_selection(self):
        result = select((ROOT/'vendor/mcc2021/index.html').read_bytes(),
                        (ROOT/'benchmarks/publication-selection.json').read_bytes())
        self.assertEqual(result, json.loads((ROOT/'benchmarks/stress-selection.json').read_text()))
        previous = json.loads((ROOT/'benchmarks/publication-selection.json').read_text())
        families = {r['family'] for r in previous['models'] if r['split'] == 'development'}
        self.assertLessEqual({r['family'] for r in result['models']}, families)
        self.assertEqual(result['expected_properties'], 16*len(result['models']))
        self.assertTrue(all('sha256' not in r for r in result['models']))

    def test_order_is_published_order_and_no_outcomes(self):
        names = ['big', 'small', 'z', 'a', 'y', 'b']
        index = ''.join(f'INPUTS/F-PT-{name}.tgz"' for name in names).encode()
        prior = dict(models=[dict(family='F', name='F-PT-small', published_ordinal=2, split='development'),
                             dict(family='E', name='ignored', published_ordinal=1, split='evaluation')])
        result = select(index, json.dumps(prior).encode())
        self.assertEqual([r['name'] for r in result['models']], ['F-PT-a', 'F-PT-y', 'F-PT-b'])
        self.assertEqual([r['published_ordinal'] for r in result['models']], [4, 5, 6])

    def test_fewer_than_three_and_no_larger_instances(self):
        for total, expected in [(2, []), (3, [3]), (4, [3, 4])]:
            index = ''.join(f'INPUTS/F-PT-{i}.tgz"' for i in range(1, total+1)).encode()
            prior = dict(models=[dict(family='F', name='F-PT-2', published_ordinal=2, split='development')])
            self.assertEqual([r['published_ordinal'] for r in select(index, json.dumps(prior).encode())['models']], expected)

    def test_rejects_stale_prior_ordinal(self):
        with self.assertRaisesRegex(ValueError, 'ordinal'):
            select(b'INPUTS/F-PT-a.tgz"', json.dumps(dict(models=[dict(
                family='F', name='F-PT-b', published_ordinal=1, split='development')])).encode())


if __name__ == '__main__':
    unittest.main()
