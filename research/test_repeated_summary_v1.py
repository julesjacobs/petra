import importlib.util
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location('summary',Path(__file__).with_name('summarize-repeated-comparison-linux-v1.py'))
summary=importlib.util.module_from_spec(spec)
spec.loader.exec_module(summary)

class SummaryTests(unittest.TestCase):
    def test_false_property_answer_is_solved(self):
        row=dict(property_truth=False,verdict='reachable',wall_seconds=0.25)
        self.assertTrue(summary.solved(row))
        self.assertEqual(summary.par2(row,30),0.25)

    def test_unknown_and_errors_receive_the_registered_penalty(self):
        for verdict in ['unknown','error','unsupported']:
            self.assertEqual(summary.par2(dict(verdict=verdict,property_truth=None,wall_seconds=0.1),30),60)

    def test_missing_measurements_are_not_zero(self):
        self.assertEqual(summary.stats([None,float('nan'),float('inf'),False]),dict(observations=0,median=None,minimum=None,maximum=None))
        self.assertEqual(summary.stats([None,0,2,4]),dict(observations=3,median=2,minimum=0,maximum=4))

    def test_solved_rows_require_finite_nonnegative_wall_time(self):
        for wall in [None,-1,float('nan'),float('inf'),False]:
            with self.assertRaises(AssertionError):
                summary.par2(dict(property_truth=True,verdict='unreachable',wall_seconds=wall),5)

class SummaryIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='pvass-summary-fixture-')
        self.root=Path(self.temp.name)
        self.original=(summary.ROOT,summary.F)
        (self.root/'research').mkdir()
        (self.root/'scripts').mkdir()
        for relative in ['research/audit-general-development-v3-linux-v1.py','scripts/analyze_application_expansion.py']:
            shutil.copyfile(summary.ROOT/relative,self.root/relative)
        summary.ROOT=self.root
        summary.F=self.root/'research/repeated-comparison-linux-v1'
        summary.F.mkdir()
        self.methods=['native-reduced','native-frozen','verifypn-default','smpt-mcc-portable']
        self.blocks=[]
        self.rows={}
        self.cases=[dict(query=f'q{i:03}',representative=f'q{0 if i==175 else i:03}') for i in range(176)]
        for index,budget in enumerate([5,30,30,5,5,30]):
            name=f'b{index+1}-{budget}s'
            folder=summary.F/name
            folder.mkdir()
            output=self.root/'results'/name
            output.mkdir(parents=True)
            (folder/'plan.json').write_text(json.dumps(dict(output=str(output.relative_to(self.root)))))
            for filename in ['execution.json','terminal.json','capability.json']:
                (folder/filename).write_text('{}')
            self.blocks.append(dict(name=name,seconds=budget,plan_sha256=summary.sha(folder/'plan.json')))
            rows=[]
            for i in range(176):
                representative=0 if i==175 else i
                for method in self.methods:
                    accepted=(method=='native-reduced' and (representative in [0,1] or representative==2 and index in [0,4])) or (method=='native-frozen' and representative in [0,3])
                    resources=dict(systemd_result='success' if accepted else 'timeout',peak_memory_bytes=4096,
                        perf_counters={counter:dict(value=100,time_running_percent=100,event_runtime_ns=1)
                                       for counter in ['instructions:u','cycles:u','task-clock']})
                    if index==4 and representative==0 and method=='native-reduced':
                        resources['perf_counters'].pop('cycles:u')
                    row=dict(query=f'q{i:03}',method=method,repeat=0,
                        property_truth=False if accepted else None,verdict='reachable' if accepted else 'unknown',
                        wall_seconds=(1 if method=='native-reduced' else 2) if accepted else budget+0.03,
                        resources=resources,exit_code=0 if accepted else 124,outer_timeout=not accepted)
                    if accepted and method.startswith('native-'):row['validation']=dict(wall_seconds=0.2)
                    rows.append(row)
            self.rows[name]=rows
        self.suite=dict(methods=self.methods,blocks=self.blocks)
        (summary.F/'suite.json').write_text(json.dumps(self.suite))
        (summary.F/'terminal.json').write_text(json.dumps(dict(suite_sha256=summary.sha(summary.F/'suite.json'),exit_code=0,completed=[b['name'] for b in self.blocks])))
        self.refresh()

    def tearDown(self):
        summary.ROOT,summary.F=self.original
        self.temp.cleanup()

    def refresh(self):
        pins={}
        for block in self.blocks:
            folder=summary.F/block['name']
            raw=self.root/'results'/block['name']/'runs.jsonl'
            raw.write_text(''.join(json.dumps(row)+'\n' for row in self.rows[block['name']]))
            pins[str(raw.relative_to(self.root))]=summary.sha(raw)
            audit=dict(status='passed',audit_issues=[],invalid_rows=[],warnings=[],
                artifact_sha256={str(raw.relative_to(self.root)):summary.sha(raw),
                                 str((folder/'plan.json').relative_to(self.root)):summary.sha(folder/'plan.json')},
                full_rows=self.rows[block['name']],classification=dict(cases=self.cases))
            (folder/'audit.json').write_text(json.dumps(audit))
        (summary.F/'collection.json').write_text(json.dumps(dict(suite_sha256=summary.sha(summary.F/'suite.json'),files_sha256=pins)))

    def run_summary(self):
        with contextlib.redirect_stdout(io.StringIO()):summary.main()
        return json.loads((summary.F/'summary.json').read_text())

    def test_complete_synthetic_matrix_has_known_metrics(self):
        report=self.run_summary()
        budget=report['budgets']['5']
        self.assertEqual(len(report['blocks']),6)
        self.assertEqual(budget['per_query']['q002']['native-reduced']['solved_frequency'],2)
        self.assertEqual(budget['representative_solved_intersection']['native-reduced'],['q000','q001'])
        self.assertEqual(budget['representative_solved_union']['native-reduced'],['q000','q001','q002'])
        self.assertAlmostEqual(budget['methods']['native-reduced']['representative_par2_mean_seconds'],(8+517*10)/525)
        self.assertAlmostEqual(budget['methods']['native-reduced']['all_property_par2_mean_seconds'],(11+517*10)/528)
        timing=budget['common_solved_timings']['native-frozen']
        self.assertEqual(timing['queries'],['q000'])
        self.assertAlmostEqual(timing['geometric_mean_baseline_over_candidate'],2)
        data=budget['per_query']['q000']['native-reduced']
        self.assertEqual(data['counters']['cycles:u']['values']['observations'],2)
        self.assertEqual(data['validation_wall_seconds']['median'],0.2)

    def test_readable_report_preserves_repeat_and_counter_limitations(self):
        self.run_summary()
        report=(summary.F/'report.md').read_text()
        five,thirty=report.split('## 30-second budget',1)
        self.assertIn('| native-reduced | 3, 2, 3 | 2 | 3 | 9.862857 | 4, 3, 4 | 9.812500 |',five)
        self.assertIn('| native-reduced | 2, 2, 2 | 2 | 2 |',thirty)
        self.assertIn('| b1-5s | native-frozen | 2 | 1 |',five)
        self.assertIn('| b4-5s | native-frozen | 1 | 1 |',five)
        self.assertIn('| native-frozen | 1 | 2.000000 |',five)
        self.assertIn('| verifypn-default | 0 | unavailable |',five)
        self.assertIn('| native-reduced | cycles:u | full-coverage: 526, missing-or-invalid-value: 2 |',five)
        self.assertIn('not a full-cohort speed claim',report)
        self.assertIn('including unsuccessful runs',report)

    def test_readable_report_rejects_incomplete_status(self):
        with self.assertRaises(AssertionError):
            summary.markdown_report(dict(status='running'))

    def test_rejects_a_changed_downloaded_row(self):
        raw=self.root/'results'/self.blocks[0]['name']/'runs.jsonl'
        raw.write_text(raw.read_text()+'\n')
        with self.assertRaises(AssertionError):self.run_summary()

    def test_rejects_cross_block_answer_disagreement(self):
        for row in self.rows[self.blocks[0]['name']]:
            if row['query']=='q001' and row['method']=='native-reduced':
                row.update(verdict='unreachable',property_truth=True)
        self.refresh()
        with self.assertRaisesRegex(AssertionError,'Cross-block answer disagreement'):self.run_summary()

    def test_rejects_cross_block_disagreement_between_duplicate_queries(self):
        for index,block in enumerate(self.blocks):
            for row in self.rows[block['name']]:
                if row['query']=='q000' and index==0 or row['query']=='q175' and index!=0:
                    row.update(verdict='unknown',property_truth=None)
                elif row['query']=='q175' and index==0 and summary.solved(row):
                    row.update(verdict='unreachable',property_truth=True)
        self.refresh()
        with self.assertRaisesRegex(AssertionError,'Cross-block duplicate disagreement'):self.run_summary()

if __name__=='__main__':unittest.main()
