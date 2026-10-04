import copy
import json
from pathlib import Path
import tempfile
import unittest

from linux_benchmark_segments import combine, digest, schedule, selection


class SegmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.prior, self.next = self.root / 'prior', self.root / 'next'
        self.manifest = self.root / 'manifest.json'
        self.manifest.write_text(json.dumps({'queries': [{'name': x} for x in ['a', 'b', 'c']]}))
        for d in (self.prior, self.next):
            (d / 'runner-source').mkdir(parents=True)
        old = 'import csv\n    except FileNotFoundError:\n        return\n'
        new = old.replace('import csv\n', 'import csv\nimport errno\n').replace(
            '    except FileNotFoundError:\n        return\n',
            '    except OSError as error:\n        if error.errno in (errno.ENOENT, errno.ENODEV):\n            return\n        raise\n')
        for directory, source in [(self.prior, old), (self.next, new)]:
            (directory / 'runner-source/linux_runner.py').write_text(source)
        (self.next / 'runner-source/linux_benchmark_segments.py').write_text('driver')
        self.previous = dict(property_order=['a', 'b', 'c'], methods=['x', 'y'], repeat=2,
                             order_seed=99, queries=3, seconds=5, native_original=True,
                             native_python='python', native_python_sha256='abc', perf=True,
                             linux_cpus=[8], memory_mib=2048, verifypn={'binary_sha256': 'def'},
                             manifest_sha256=digest(self.manifest),
                             linux_host=dict(topology='cpu8', kernel='kernel', perf_event_paranoid='2', loadavg='old'),
                             script_sha256={'linux_runner.py': digest(self.prior / 'runner-source/linux_runner.py')})
        self.first = [dict(query=q, method=m, repeat=r, verdict='unknown') for q, m, r in list(schedule(self.previous))[:6]]
        self.provenance = dict(retained_complete_properties=['a'], rerun_properties=['b', 'c'],
                               full_property_order=self.previous['property_order'],
                               continuation_script_sha256=digest(self.next / 'runner-source/linux_benchmark_segments.py'))
        self.current = copy.deepcopy(self.previous)
        self.current.update(queries=2, property_order=['b', 'c'])
        self.current['script_sha256']['linux_runner.py'] = digest(self.next / 'runner-source/linux_runner.py')
        self.second = [dict(query=q, method=m, repeat=r, verdict='reachable') for q, m, r in schedule(self.previous, {'b', 'c'})]
        self.save()

    def save(self):
        (self.prior / 'environment.json').write_text(json.dumps(self.previous))
        (self.prior / 'runs.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in self.first))
        self.provenance.update(prior_records_sha256=digest(self.prior / 'runs.jsonl'),
                               prior_environment_sha256=digest(self.prior / 'environment.json'))
        self.current['continuation'] = self.provenance
        (self.next / 'environment.json').write_text(json.dumps(self.current))
        (self.next / 'SEGMENT.json').write_text(json.dumps(self.provenance))
        (self.next / 'runs.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in self.second))

    def combine(self):
        return combine(self.prior, self.next, self.manifest, self.root / 'combined')

    def test_complete_groups_retained_in_original_rotation(self):
        self.assertEqual(self.combine(), 12)
        env = json.loads((self.root / 'combined/environment.json').read_text())
        self.assertTrue(env['native_original'])
        self.assertTrue(env['perf'])
        self.assertEqual(env['linux_cpus'], [8])
        data = [json.loads(x) for x in (self.root / 'combined/runs.jsonl').read_text().splitlines()]
        self.assertEqual([r['verdict'] for r in data[:4]], ['unknown']*4)
        self.assertEqual(data[4]['verdict'], 'reachable')

    def test_rejects_native_perf_or_competitor_configuration_changes(self):
        for field, value in [('native_original', False), ('perf', False), ('linux_cpus', [9]),
                             ('memory_mib', 4096), ('native_python_sha256', 'other'),
                             ('verifypn', {'binary_sha256': 'other'})]:
            original = self.current[field]
            self.current[field] = value
            self.save()
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'configuration'):
                self.combine()
            self.current[field] = original

    def test_rejects_outcome_selected_retention(self):
        self.provenance['retained_complete_properties'] = []
        self.save()
        with self.assertRaisesRegex(ValueError, 'retention'):
            self.combine()

    def test_rejects_missing_duplicate_or_reset_rotation(self):
        original = self.second
        variants = [original[:-1], original+[original[-1]], [original[1], original[0], *original[2:]]]
        for second in variants:
            self.second = second
            self.save()
            with self.assertRaisesRegex(ValueError, 'rotation'):
                self.combine()

    def test_rejects_source_or_record_mutation(self):
        (self.prior / 'runs.jsonl').write_text('{}\n')
        with self.assertRaisesRegex(ValueError, 'Prior segment changed'):
            self.combine()
        self.save()
        (self.next / 'runner-source/linux_runner.py').write_text('arbitrary change')
        with self.assertRaisesRegex(ValueError, 'Snapshot'):
            self.combine()

    def test_rejects_nonprefix_prior(self):
        with self.assertRaisesRegex(ValueError, 'prefix'):
            selection(self.previous, self.first[::-1])


if __name__ == '__main__':
    unittest.main(verbosity=2)
