import unittest
import tempfile
from pathlib import Path
from import_fastforward_benchmarks import pnml_text, property_text, inequalities
from smpt_import import pnml, properties
from audit_fastforward_benchmarks import parse_net, parse_formula, canonical_branches

NET = '''PLACE java.Object[],x,y; MARKING x: 2;
TRANSITION <read<java.Object[],x>>
CONSUME x: 2;
PRODUCE y: 3, x: 2;
TRANSITION source
CONSUME ;
PRODUCE java.Object[]: 1;
'''

class FastForwardImportTests(unittest.TestCase):
    def test_weights_reads_and_identifier_map(self):
        net = parse_net(NET)
        self.assertEqual(net['places'], ['java.Object[]', 'x', 'y'])
        self.assertEqual(net['initial'], [0, 2, 0])
        self.assertEqual(net['transitions'][0]['pre'], [[1, 2]])
        self.assertEqual(net['transitions'][0]['post'], [[1, 2], [2, 3]])
        self.assertEqual(net['transitions'][1]['pre'], [])

    def test_exact_zero_constraints_survive(self):
        net = parse_net(NET)
        branches = canonical_branches(net, parse_formula('EF (x = 0 AND y >= 3 AND java.Object[] >= 0)', net['places']))
        self.assertEqual(branches[0]['target'], [
            dict(coefficients=[0, 1, 0], bound=0, equality=True),
            dict(coefficients=[0, 0, 1], bound=3, equality=False)])

    def test_disjunction_and_conjunction(self):
        got = parse_formula('EF ((x=1 OR y=2) AND java.Object[]>=3)', ['java.Object[]', 'x', 'y'])
        self.assertEqual(got, [[(1, 1, True), (0, 3, False)], [(2, 2, True), (0, 3, False)]])

    def test_net_rejects_unsupported_and_duplicate_syntax(self):
        for text in (NET + 'garbage', NET.replace('PLACE java.Object[],x,y;', 'PLACE java.Object[],,x,y;'), NET.replace('x: 2;', 'x: 2,x: 1;', 1),
                     NET.replace('PRODUCE y: 3', 'PRODUCE absent: 3'),
                     NET.replace('MARKING x: 2;', 'MARKING x: -1;'),
                     NET.replace('PLACE ', 'PLACE SAFE '),
                     NET.replace('TRANSITION source', 'TRANSITION <read<java.Object[],x>>')):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    parse_net(text)

    def test_zero_arcs_are_semantically_empty(self):
        net = parse_net(NET.replace('CONSUME x: 2;', 'CONSUME x: 0;'))
        self.assertEqual(net['transitions'][0]['pre'], [])

    def test_independent_pnml_xml_roundtrip_preserves_exact_zero_and_weighted_read(self):
        net = parse_net(NET)
        predicates = parse_formula('EF ((x=0 AND y>=3) OR java.Object[]=2)', net['places'])
        with tempfile.TemporaryDirectory() as directory:
            model, formula = Path(directory) / 'model.pnml', Path(directory) / 'property.xml'
            model.write_text(pnml_text(net))
            formula.write_text(property_text(inequalities(predicates)))
            imported = pnml(model)
            self.assertEqual(imported['initial'], [0, 2, 0])
            self.assertEqual(imported['transitions'][0]['pre'], [(1, 2)])
            self.assertEqual(imported['transitions'][0]['post'], [(1, 2), (2, 3)])
            targets = properties(formula, imported)[0]['targets']
            self.assertEqual(targets, [[
                dict(coefficients=[0, -1, 0], bound=0, equality=False),
                dict(coefficients=[0, 0, 1], bound=3, equality=False)], [
                dict(coefficients=[1, 0, 0], bound=2, equality=False),
                dict(coefficients=[-1, 0, 0], bound=-2, equality=False)]])

    def test_formula_rejects_unsupported_or_trailing_syntax(self):
        for text in ('AG (x=0)', 'EF (x <= 1)', 'EF (x=0) garbage',
                     'EF (z=0)', 'EF (x< = 1)', 'EF (x=0', 'EF x=-1', 'EF x=9223372036854775808'):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    parse_formula(text, ['x'])
        with self.assertRaises(ValueError):
            parse_formula('EF ((x=1 OR x=2) AND (x=3 OR x=4))', ['x'], max_branches=3)
        with self.assertRaises(ValueError):
            parse_formula('EF (x=0) AND y=1', ['x', 'y'])

if __name__ == '__main__':
    unittest.main()
