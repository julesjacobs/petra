import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from its_adapter import parse_result, stage_property, local_name


class ItsAdapterTests(unittest.TestCase):
    def test_truth_and_polarity(self):
        for kind in ('EF', 'AG'):
            for truth in ('TRUE', 'FALSE'):
                output = f'FORMULA q.extra FALSE\nFORMULA q {truth} TECHNIQUES DECISION_DIAGRAMS\n'
                result = parse_result(output, 'q', kind, 0)
                self.assertEqual(result['property_truth'], truth == 'TRUE')
                self.assertEqual(result['verdict'], 'reachable' if (truth == 'TRUE') == (kind == 'EF') else 'unreachable')

    def test_untrusted_or_failed_results(self):
        for output, code, timeout, reason in [
            ('FORMULA qq TRUE', 0, False, 'missing-result'),
            ('FORMULA q TRUE\nFORMULA q FALSE', 0, False, 'conflicting-verdicts'),
            ('FORMULA q TRUE garbage', 0, False, 'malformed-result'),
            ('FORMULA q CANNOT_COMPUTE', 0, False, 'malformed-result'),
            ('FORMULA q TRUE', 1, False, 'nonzero-exit'),
            ('FORMULA q TRUE', 0, True, 'timeout'),
        ]:
            result = parse_result(output, 'q', 'EF', code, timeout)
            self.assertEqual(result['reason'], reason)
            self.assertEqual(result['verdict'], 'unknown')
        self.assertEqual(parse_result('FORMULA q TRUE\nFORMULA q TRUE', 'q', 'EF', 0)['verdict'], 'reachable')

    def test_single_property_staging(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model = root / 'original.pnml'
            model.write_bytes(b'<pnml>unchanged bytes</pnml>\n')
            xml = root / 'props.xml'
            prop = '<property><id>{}</id><formula><all-paths><globally><integer-le><tokens-count><place>p</place></tokens-count><integer-constant>2</integer-constant></integer-le></globally></all-paths></formula></property>'
            xml.write_text('<property-set xmlns="urn:test">' + prop.format('other') + prop.format('q') + '</property-set>')
            record = stage_property(model, xml, 'q', root / 'stage')
            self.assertEqual(record['kind'], 'AG')
            self.assertEqual((root / 'stage/model.pnml').read_bytes(), model.read_bytes())
            staged = ET.parse(root / 'stage/ReachabilityCardinality.xml').getroot()
            self.assertEqual(len(staged), 1)
            self.assertEqual(next(e.text for e in staged.iter() if local_name(e) == 'id'), 'q')
            self.assertNotIn('ns0:', (root / 'stage/ReachabilityCardinality.xml').read_text())
            with self.assertRaises(FileExistsError):
                stage_property(model, xml, 'q', root / 'stage')
            with self.assertRaises(ValueError):
                stage_property(model, xml, 'missing', root / 'missing')
            xml.write_text('<property-set>' + prop.format('q') * 2 + '</property-set>')
            with self.assertRaises(ValueError):
                stage_property(model, xml, 'q', root / 'duplicate')


if __name__ == '__main__':
    unittest.main()
