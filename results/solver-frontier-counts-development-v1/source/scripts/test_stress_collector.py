import io
import json
from pathlib import Path
import tarfile
import tempfile
import sys
import unittest
from unittest.mock import Mock, patch

from collect_stress_mcc import (ArtifactBudget, ArtifactLimit, bounded_worker, collect, planned_slots,
                                safe_extract, tina_chunks, worker, write_json, write_text_chunks)


class PreflightTests(unittest.TestCase):
    def test_racing_process_does_not_hide_active_driver(self):
        from collect_stress_mcc import ROOT, workload_preflight
        raced = Mock(pid=-1)
        raced.name.side_effect = SystemError('racing sysctl')
        active = Mock(pid=-2)
        active.name.return_value = 'python'
        active.cmdline.return_value = ['python', 'scripts/benchmark_smpt_classic.py']
        active.cwd.return_value = str(ROOT)
        active.status.return_value = 'running'
        with patch('process_runner.workspace_workloads', return_value=[]), \
                patch('psutil.process_iter', return_value=[raced, active]):
            with self.assertRaisesRegex(RuntimeError, 'Active workspace workloads'):
                workload_preflight()

    def test_racing_process_alone_does_not_abort(self):
        from collect_stress_mcc import workload_preflight
        raced = Mock(pid=-1)
        raced.cmdline.side_effect = SystemError('racing sysctl')
        with patch('process_runner.workspace_workloads', return_value=[]), \
                patch('psutil.process_iter', return_value=[raced]):
            workload_preflight()


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.row = dict(name='F-PT-1', family='F', split='stress-development', expected_properties=16)
        self.guard = patch('collect_stress_mcc.workload_preflight').start()
        self.addCleanup(patch.stopall)

    def archive(self, members):
        path = self.root/'test.tgz'
        with tarfile.open(path, 'w:gz') as tar:
            for name, content, kind in members:
                info = tarfile.TarInfo(name)
                info.type = kind
                info.size = len(content) if kind == tarfile.REGTYPE else 0
                tar.addfile(info, io.BytesIO(content) if kind == tarfile.REGTYPE else None)
        return path

    def test_safe_regular_files(self):
        archive = self.archive([('F-PT-1/model.pnml', b'net', tarfile.REGTYPE),
                                ('F-PT-1/ReachabilityCardinality.xml', b'xml', tarfile.REGTYPE)])
        self.assertEqual(safe_extract(archive, self.root/'inputs', 'F-PT-1', 100), 6)
        self.assertEqual((self.root/'inputs/F-PT-1/model.pnml').read_bytes(), b'net')

    def test_rejects_paths_links_devices_duplicates_and_size(self):
        cases = [[('../outside', b'x', tarfile.REGTYPE)], [('/absolute', b'x', tarfile.REGTYPE)],
                 [('F-PT-1/link', b'', tarfile.SYMTYPE)], [('F-PT-1/hard', b'', tarfile.LNKTYPE)],
                 [('F-PT-1/device', b'', tarfile.CHRTYPE)],
                 [('F-PT-1/model.pnml', b'x', tarfile.REGTYPE)]*2,
                 [('F-PT-1/model.pnml', b'x'*101, tarfile.REGTYPE)]]
        for index, members in enumerate(cases):
            with self.subTest(case=index), self.assertRaises(ValueError):
                safe_extract(self.archive(members), self.root/f'inputs-{index}', 'F-PT-1', 100)
        self.assertFalse((self.root/'outside').exists())

    def test_failure_slots_have_no_invented_ids(self):
        unknown = planned_slots(self.row, 'timeout')
        self.assertEqual(len(unknown), 16)
        self.assertTrue(all(not r['observed'] and 'property_id' not in r and 'kind' not in r for r in unknown))
        observed = planned_slots(self.row, 'parse failed', [{'property_id': 'actual-id'}])
        self.assertTrue(observed[0]['observed'])
        self.assertEqual(observed[0]['property_id'], 'actual-id')
        self.assertFalse(observed[1]['observed'])

    def test_all_failed_models_keep_all_slots_and_selection_immutable(self):
        selection = self.root/'selection.json'
        row = dict(self.row, url='https://invalid.example/input.tgz')
        selection.write_text(json.dumps(dict(format='mcc-stress-selection-v1', source='source',
                                             expected_properties=16, models=[row])))
        before = selection.read_bytes()
        usage = dict(exit_code=-9, wall_seconds=1, sampled_peak_rss_bytes=200,
                     termination_reason='timeout', memory_limit_bytes=1024)
        with patch('collect_stress_mcc.bounded_worker', return_value=usage):
            collect(selection, self.root/'out', 1, 1, 1, 1)
        manifest = json.loads((self.root/'out/manifest.json').read_text())
        self.assertTrue(manifest['collection_complete'])
        self.assertEqual(len(manifest['queries']), 16)
        self.assertTrue(all(not q['observed'] for q in manifest['queries']))
        self.assertEqual(selection.read_bytes(), before)
        with self.assertRaisesRegex(ValueError, 'overwrite'):
            collect(selection, self.root/'out', 1, 1, 1, 1)

    def test_writes_stop_before_artifact_limit(self):
        budget = ArtifactBudget(8)
        path = self.root/'artifact'
        with self.assertRaises(ArtifactLimit):
            write_text_chunks(path, ['12345', '6789'], budget)
        self.assertEqual(path.read_bytes(), b'12345')
        self.assertEqual(budget.stats()['used_bytes'], 5)

    def test_streamed_tina_matches_existing_importer(self):
        from smpt_import import tina
        model = dict(initial=[1, 0], transitions=[dict(pre=[[0, 1]], post=[[1, 2]])])
        self.assertEqual(''.join(tina_chunks(model)), tina(model))

    def test_preflight_refuses_active_workloads_before_creating_corpus(self):
        selection = self.root/'selection.json'
        selection.write_text(json.dumps(dict(format='mcc-stress-selection-v1', source='source',
                                             expected_properties=16, models=[self.row])))
        self.guard.side_effect = RuntimeError('Active workspace workloads prohibit collection')
        with self.assertRaisesRegex(RuntimeError, 'Active workspace'), patch('collect_stress_mcc.bounded_worker') as run:
            collect(selection, self.root/'out', 1, 1, 1, 1)
        run.assert_not_called()
        self.assertFalse((self.root/'out').exists())

    def test_preflight_between_workers_preserves_pending_slots(self):
        selection = self.root/'selection.json'
        other = dict(self.row, name='F-PT-2')
        selection.write_text(json.dumps(dict(format='mcc-stress-selection-v1', source='source',
                                             expected_properties=32, models=[self.row, other])))
        self.guard.side_effect = [None, None, RuntimeError('Active workspace workloads prohibit collection')]
        usage = dict(exit_code=-9, wall_seconds=1, sampled_peak_rss_bytes=20, termination_reason='timeout')
        with patch('collect_stress_mcc.bounded_worker', return_value=usage) as run:
            with self.assertRaisesRegex(RuntimeError, 'Active workspace'):
                collect(selection, self.root/'out', 1, 1, 1, 1)
        self.assertEqual(run.call_count, 1)
        manifest = json.loads((self.root/'out/manifest.json').read_text())
        self.assertFalse(manifest['collection_complete'])
        self.assertEqual(len(manifest['queries']), 32)
        self.assertTrue(all(q['error'] == 'collection not attempted' for q in manifest['queries'][16:]))

    def test_artifact_failure_keeps_slots_and_reports_bytes(self):
        selection = self.root/'selection.json'
        selection.write_text(json.dumps(dict(format='mcc-stress-selection-v1', source='source',
                                             expected_properties=16, models=[self.row])))
        def limited(command, cwd, seconds, memory_bytes, log):
            request = json.loads(Path(command[-1]).read_text())
            output, job = Path(request['output']), Path(request['job'])
            (output/'archives/F-PT-1.part').write_bytes(b'12345')
            write_json(job/'progress.json', dict(stage='failed', failure_reason='artifact-limit',
                       error='ArtifactLimit', observed_properties=[{'property_id': 'observed-real-id'}]))
            return dict(exit_code=1, wall_seconds=0.1, sampled_peak_rss_bytes=5000, termination_reason=None)
        with patch('collect_stress_mcc.bounded_worker', side_effect=limited):
            collect(selection, self.root/'out', 1, 1, 1, 1, artifact_mib=1)
        manifest = json.loads((self.root/'out/manifest.json').read_text())
        outcomes = json.loads((self.root/'out/collection-outcomes.json').read_text())
        self.assertEqual(len(manifest['queries']), 16)
        self.assertEqual(manifest['queries'][0]['property_id'], 'observed-real-id')
        self.assertTrue(all(q['status'] == 'unsupported' for q in manifest['queries']))
        self.assertFalse(manifest['queries'][1]['observed'])
        self.assertEqual(outcomes[0]['resources']['termination_reason'], 'artifact-limit')
        self.assertEqual(outcomes[0]['resources']['artifacts']['used_bytes'], 5)
        self.assertEqual(outcomes[0]['resources']['artifacts']['limit_bytes'], 1024**2)
        self.assertEqual(self.guard.call_count, 2)
        self.assertTrue((self.root/'out/collector-source/smpt_import.py').exists())
        self.assertIn('version', json.loads((self.root/'out/collector-provenance.json').read_text())['runtime'])

    def test_worker_timeout_records_resource_failure(self):
        result = bounded_worker([sys.executable, '-c', 'import time; time.sleep(30)'],
                                self.root, 0.1, 128*1024**2, self.root/'timeout.log')
        self.assertEqual(result['termination_reason'], 'timeout')
        self.assertNotEqual(result['exit_code'], 0)
        self.assertGreater(result['wall_seconds'], 0)
        self.assertGreater(result['sampled_peak_rss_bytes'], 0)

    def test_worker_success_uses_actual_ids_and_canonical_manifest_fields(self):
        pnml = '<pnml><net id="n" type="http://www.pnml.org/version-2009/grammar/ptnet"><page id="page"><place id="p"><initialMarking><text>1</text></initialMarking></place></page></net></pnml>'
        formula = '<formula><exists-path><finally><integer-le><integer-constant>1</integer-constant><tokens-count><place>p</place></tokens-count></integer-le></finally></exists-path></formula>'
        xml = '<property-set>'+''.join(f'<property><id>real-{i}</id>{formula}</property>' for i in range(16))+'</property-set>'
        archive = self.archive([('F-PT-1/model.pnml', pnml.encode(), tarfile.REGTYPE),
                                ('F-PT-1/ReachabilityCardinality.xml', xml.encode(), tarfile.REGTYPE)])
        output, job = self.root/'out', self.root/'job'
        (output/'archives').mkdir(parents=True)
        job.mkdir()
        request = job/'request.json'
        write_json(request, dict(model=dict(self.row, url=archive.as_uri()), output=str(output), job=str(job),
                                 memory_bytes=1024**3, archive_bytes=1024**2, expanded_bytes=1024**2, artifact_bytes=4*1024**2))
        with patch('collect_stress_mcc.sys.platform', 'darwin'):
            self.assertEqual(worker(request), 0)
        records = json.loads((job/'records.json').read_text())
        self.assertEqual(len(records), 16)
        self.assertEqual(records[9]['property_id'], 'real-9')
        self.assertEqual(records[9]['kind'], 'EF')
        self.assertTrue(all(record['status'] == 'imported' and record['observed'] for record in records))
        for record in records:
            self.assertTrue((output/record['pnml']).exists())
            self.assertTrue((output/record['branches'][0]['path']).exists())

    def test_worker_net_failure_retains_observed_property_ids(self):
        xml = '<property-set>'+''.join(f'<property><id>actual-{i}</id></property>' for i in range(16))+'</property-set>'
        archive = self.archive([('F-PT-1/model.pnml', b'invalid xml', tarfile.REGTYPE),
                                ('F-PT-1/ReachabilityCardinality.xml', xml.encode(), tarfile.REGTYPE)])
        output, job = self.root/'out', self.root/'job'
        (output/'archives').mkdir(parents=True)
        job.mkdir()
        request = job/'request.json'
        write_json(request, dict(model=dict(self.row, url=archive.as_uri()), output=str(output), job=str(job),
                                 memory_bytes=1024**3, archive_bytes=1024**2, expanded_bytes=1024**2, artifact_bytes=4*1024**2))
        with patch('collect_stress_mcc.sys.platform', 'darwin'):
            self.assertEqual(worker(request), 1)
        progress = json.loads((job/'progress.json').read_text())
        self.assertEqual(progress['stage_failed'], 'parse-net')
        self.assertEqual(len(progress['observed_properties']), 16)
        self.assertEqual(progress['observed_properties'][7]['property_id'], 'actual-7')
        self.assertIn('sha256', progress['archive'])


if __name__ == '__main__':
    unittest.main()
