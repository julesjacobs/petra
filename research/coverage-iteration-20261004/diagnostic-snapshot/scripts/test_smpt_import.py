#!/usr/bin/env python3
import itertools
import pathlib
import random
import tempfile
import unittest
import xml.etree.ElementTree as ET

from smpt_import import dnf, pnml, properties, xml_tree
from benchmark_smpt_classic import aggregate, property_truth

ROOT = pathlib.Path(__file__).resolve().parents[1]


def evaluate(node, marking):
    if node.tag == 'integer-constant':
        return int(node.text)
    if node.tag == 'tokens-count':
        return sum(marking[p.text.strip()] for p in node)
    if node.tag == 'integer-le':
        return evaluate(node[0], marking) <= evaluate(node[1], marking)
    if node.tag == 'negation':
        return not evaluate(node[0], marking)
    if node.tag == 'conjunction':
        return all(evaluate(n, marking) for n in node)
    if node.tag == 'disjunction':
        return any(evaluate(n, marking) for n in node)
    raise ValueError(node.tag)


def accepts(targets, marking):
    return any(all(sum(a*x for a, x in zip(c['coefficients'], marking)) >= c['bound']
                   for c in conjunction) for conjunction in targets)


class ImportTests(unittest.TestCase):
    def test_arcs_marking_and_ids(self):
        text = '''<pnml xmlns="urn:test"><net id="n" type="http://www.pnml.org/version-2009/grammar/ptnet"><page id="g">
          <place id="p"><name><text>display name</text></name><initialMarking><text>7</text></initialMarking></place>
          <place id="q"/><transition id="t"/>
          <arc id="a" source="p" target="t"><inscription><text>2</text><graphics/></inscription></arc>
          <arc id="b" source="p" target="t"/>
          <arc id="c" source="t" target="p"><inscription><text>3</text></inscription></arc>
          <arc id="d" source="t" target="q"/>
        </page></net></pnml>'''
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory)/'model.pnml'
            path.write_text(text)
            model = pnml(path)
            self.assertEqual(model['places'], ['p', 'q'])
            self.assertEqual(model['initial'], [7, 0])
            self.assertEqual(model['transitions'], [dict(name='t', pre=[(0, 3)], post=[(0, 3), (1, 1)])])
            for bad in [text.replace('source="p" target="t"', 'source="p" target="q"'),
                        text.replace('<text>2</text>', '<text>0</text>'),
                        text.replace('<arc id="a"', '<arc type="inhibitor" id="a"'),
                        text.replace('<transition id="t"/>', '<transition id="t"><delay>1</delay></transition>'),
                        text.replace('<place id="q"/>', '<place id="p"/>')]:
                path.write_text(bad)
                with self.assertRaises(ValueError):
                    pnml(path)

    def test_boolean_negation_and_strict_boundaries(self):
        formula = ET.fromstring('''<conjunction>
          <integer-le><tokens-count><place>p</place></tokens-count><integer-constant>2</integer-constant></integer-le>
          <negation><integer-le><tokens-count><place>q</place></tokens-count><tokens-count><place>p</place></tokens-count></integer-le></negation>
        </conjunction>''')
        for negate in (False, True):
            targets = dnf(formula, {'p': 0, 'q': 1}, negate)
            for p, q in itertools.product(range(5), repeat=2):
                self.assertEqual(accepts(targets, [p, q]), evaluate(formula, {'p': p, 'q': q}) != negate)
        self.assertEqual(aggregate(['unreachable', 'unknown']), 'unknown')
        self.assertEqual(aggregate(['unreachable', 'unreachable']), 'unreachable')
        self.assertEqual(aggregate(['unknown', 'reachable']), 'reachable')
        self.assertFalse(property_truth('AG', 'reachable'))
        self.assertTrue(property_truth('AG', 'unreachable'))
        self.assertTrue(property_truth('EF', 'reachable'))
        self.assertIsNone(property_truth('AG', 'unknown'))

    def test_all_published_targets_against_original_xml(self):
        source = ROOT/'vendor/smpt-benchmarks/tacas2022/Artifact'
        if not source.exists():
            self.skipTest('Run setup-smpt-benchmarks.py first')
        randomizer = random.Random(5863379)
        count = 0
        for xml in source.rglob('*.xml'):
            net = xml.parent/'model.pnml' if xml.name == 'ReachabilityCardinality.xml' else xml.with_name(xml.stem.removesuffix('_')+'.pnml')
            model = pnml(net)
            prop = properties(xml, model)[0]
            original = xml_tree(xml).find('property/formula')[0][0][0]
            samples = [model['initial']]+[[randomizer.randrange(15) for _ in model['places']] for _ in range(1000)]
            for values in samples:
                value = evaluate(original, dict(zip(model['places'], values)))
                self.assertEqual(accepts(prop['targets'], values), value if prop['kind'] == 'EF' else not value, str(xml))
            count += 1
        self.assertEqual(count, 37)


if __name__ == '__main__':
    unittest.main()
