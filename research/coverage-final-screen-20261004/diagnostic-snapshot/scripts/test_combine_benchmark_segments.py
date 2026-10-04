import hashlib
import json
import pathlib
import tempfile
import unittest

from combine_benchmark_segments import combine


class CombineTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        root = pathlib.Path(self.folder.name)
        self.prior, self.rest, self.output = (root/name for name in ('prior', 'rest', 'combined'))
        self.prior.mkdir()
        self.rest.mkdir()
        self.manifest = root/'manifest.json'
        self.manifest.write_text(json.dumps({'queries': [
            dict(name='a', family='A'), dict(name='b', family='B')]}))
        config = {key: None for key in (
            'max_states', 'platform', 'binary_sha256', 'baseline_binary_sha256',
            'scope', 'smpt_configurations', 'smpt_root', 'smpt_python', 'auto_reduce',
            'track_resources', 'smpt_original', 'outer_grace', 'memory_mib',
            'tools', 'smpt_source_sha256')}
        config.update(seconds=5, repeat=1, methods=['frozen-v2', 'portfolio-causal'],
                      manifest_sha256=hashlib.sha256(self.manifest.read_bytes()).hexdigest())
        for folder in (self.prior, self.rest):
            (folder/'environment.json').write_text(json.dumps(config))
        self.prior_rows = [self.row('a', m, 'unknown') for m in config['methods']]
        self.prior_rows.append(self.row('b', 'frozen-v2', 'reachable'))
        self.rest_rows = [self.row('b', m, 'unknown') for m in config['methods']]
        self.write_rows(self.prior, self.prior_rows)
        self.write_rows(self.rest, self.rest_rows)
        self.provenance = dict(
            prior_records_sha256=hashlib.sha256((self.prior/'runs.jsonl').read_bytes()).hexdigest(),
            retained_complete_properties=['a'], rerun_properties=['b'])
        (self.rest/'SEGMENT.json').write_text(json.dumps(self.provenance))

    @staticmethod
    def row(query, method, verdict):
        return dict(query=query, method=method, repeat=0, verdict=verdict,
                    property_truth=True if verdict == 'reachable' else None)

    @staticmethod
    def write_rows(folder, rows):
        (folder/'runs.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))

    def combine(self):
        return combine(self.prior, self.rest, self.manifest, self.output)

    def test_complete_unknown_retained_partial_success_discarded(self):
        self.assertTrue(self.combine())
        rows = [json.loads(line) for line in (self.output/'runs.jsonl').read_text().splitlines()]
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(row['verdict'] == 'unknown' for row in rows))

    def test_missing_continuation_row_rejected(self):
        self.write_rows(self.rest, self.rest_rows[:1])
        with self.assertRaisesRegex(ValueError, 'not complete'):
            self.combine()

    def test_rerunning_complete_property_rejected(self):
        self.write_rows(self.rest, self.rest_rows + [self.prior_rows[0]])
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.combine()

    def test_changed_input_or_tool_rejected(self):
        environment = self.rest/'environment.json'
        config = json.loads(environment.read_text())
        config['binary_sha256'] = 'changed'
        environment.write_text(json.dumps(config))
        with self.assertRaisesRegex(ValueError, 'binary_sha256'):
            self.combine()

    def test_cannot_select_faster_property_subset(self):
        self.provenance['retained_complete_properties'] = []
        (self.rest/'SEGMENT.json').write_text(json.dumps(self.provenance))
        with self.assertRaisesRegex(ValueError, 'all complete'):
            self.combine()


if __name__ == '__main__':
    unittest.main()
