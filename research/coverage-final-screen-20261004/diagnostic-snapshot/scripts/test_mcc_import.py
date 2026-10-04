#!/usr/bin/env python3
"""Check all collected MCC target translations against the source XML."""
import json
import random
import unittest
import argparse
import pathlib
from smpt_import import ROOT, xml_tree
from test_smpt_import import evaluate, accepts


class MCCImportTests(unittest.TestCase):
    corpus = ROOT/'benchmarks/mcc2021'
    expected = 384

    def test_original_predicates(self):
        corpus=self.corpus
        manifest=json.loads((corpus/'manifest.json').read_text())
        rng=random.Random(20210927)
        self.assertEqual(len(manifest['queries']),self.expected)
        for q in manifest['queries']:
            self.assertEqual(q['status'],'imported')
            source=ROOT/'vendor/mcc2021/inputs'/q['instance']
            root=xml_tree(source/'ReachabilityCardinality.xml')
            original=next(p for p in root if p.findtext('id')==q['property_id'])
            predicate=original.find('formula')[0][0][0]
            net=xml_tree(source/'model.pnml')
            places=[p.attrib['id'] for p in net.iter('place')]
            initial=[int(p.findtext('initialMarking/text','0')) for p in net.iter('place')]
            branches=[json.loads((corpus/b['path']).read_text()) for b in q['branches']]
            for branch in branches:
                self.assertEqual(branch['places'],places)
                self.assertEqual(branch['initial'],initial)
            samples=[initial]+[[rng.randrange(20) for _ in places] for _ in range(100)]
            for values in samples:
                truth=evaluate(predicate,dict(zip(places,values)))
                self.assertEqual(accepts([b['target'] for b in branches],values),truth if q['kind']=='EF' else not truth,q['name'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus',type=pathlib.Path,default=MCCImportTests.corpus)
    parser.add_argument('--expected',type=int,default=384)
    args=parser.parse_args()
    MCCImportTests.corpus=args.corpus.resolve()
    MCCImportTests.expected=args.expected
    unittest.main(argv=[__file__])
