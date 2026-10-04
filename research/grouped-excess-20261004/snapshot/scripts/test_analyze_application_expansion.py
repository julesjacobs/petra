import copy
import json
from pathlib import Path
import unittest

from analyze_application_expansion import analyze, corpus_groups


def fixture():
    queries = [dict(name=n, family=f, kind='EF', status='imported', branches=[dict(sha256=h)],
                    pnml=n+'.pnml', xml=n+'.xml', property_id=n)
               for n,f,h in [('all','A','a'), ('mixed','A','b'), ('none','B','c'), ('none-copy','B','c')]]
    manifest = dict(queries=queries)
    plan = dict(properties=4, expected_rows=12, methods={'native-focused':'portfolio-focused','smpt':'full','verifypn':'default'},
                smpt_configurations={'smpt':['WALK','SMT']},
                verifypn=dict(binary_sha256='vp-binary',source_commit='vp-commit',configurations={'verifypn':[]}),
                repeat=1, corpus='benchmarks/corpus', native_binary='results/frozen/vass-reach',
                native_binary_sha256='binary', validation=dict(seconds=60, memory_mib=2048, response_mib=64,
                    dag_check_max_work=200000000, included_in_solver_timing=False))
    for k,v in dict(seconds=5, max_states=2000000, memory_mib=2048, linux_cpus=[8], perf=True,
                    outer_grace=0, order_seed=1, manifest_sha256='manifest').items():
        plan[k] = v
    environment = {k:copy.deepcopy(v) for k,v in plan.items() if k not in ('properties','expected_rows','validation')}
    environment.update(methods=list(plan['methods']), property_order=[q['name'] for q in queries],
                       binary_sha256='binary',
                       native_tools={'native-focused':dict(engine='portfolio-focused',binary_sha256='binary',
                                                           binary='/workspace/pvass/results/frozen/vass-reach')},
                       bounded_validation=copy.deepcopy(plan['validation']))
    environment['bounded_validation']['enabled']=True
    rows = []
    for q in queries:
        for m in plan['methods']:
            verdict = 'reachable' if q['name']=='all' or (q['name']=='mixed' and m=='smpt') else 'unknown'
            row = dict(query=q['name'], method=m, repeat=0, verdict=verdict)
            if m=='native-focused':
                row['command']=['/workspace/pvass/results/frozen/vass-reach',
                    '--pnml','/workspace/pvass/benchmarks/corpus/'+q['pnml'],
                    '--xml','/workspace/pvass/benchmarks/corpus/'+q['xml'],
                    '--property-id',q['property_id'],'--method','portfolio-focused',
                    '--seconds','5.0','--max-states','2000000']
            if m=='native-focused' and verdict=='reachable':
                row.update(branches=[dict(branch=0,verdict='reachable',independent_check='python-witness')],
                           translation_check='independent-original-input-equals-all-canonical-branches',
                           validation=dict(exit_code=0,outer_timeout=False))
            rows.append(row)
    return manifest,plan,environment,rows


def multi_binary_fixture():
    manifest, plan, env, original_rows = fixture()
    plan['methods'] = {'native-frozen':'portfolio-focused', 'native-buffer':'portfolio-focused',
                       'native-batched':'portfolio-batched', 'smpt':'full', 'verifypn':'default'}
    plan['native_binary'] = 'results/new/vass-reach'
    plan['native_binary_sha256'] = 'new-binary'
    plan['native_tools'] = {
        'native-frozen':dict(engine='portfolio-focused', binary='/workspace/pvass/results/frozen/vass-reach', binary_sha256='binary'),
        'native-buffer':dict(engine='portfolio-focused', binary='/workspace/pvass/results/new/vass-reach', binary_sha256='new-binary'),
        'native-batched':dict(engine='portfolio-batched', binary='/workspace/pvass/results/new/vass-reach', binary_sha256='new-binary'),
    }
    plan['buffer_agglomeration_methods'] = ['native-buffer', 'native-batched']
    plan['expected_rows'] = 20
    env.update(methods=list(plan['methods']), native_tools=copy.deepcopy(plan['native_tools']),
               binary_sha256='new-binary', buffer_agglomeration_methods=['native-buffer','native-batched'])
    rows = []
    for row in original_rows:
        if row['method'] != 'native-focused':
            rows.append(row)
            continue
        for method in plan['native_tools']:
            new = copy.deepcopy(row)
            new['method'] = method
            new['command'][0] = plan['native_tools'][method]['binary']
            new['command'][8] = plan['methods'][method]
            if method != 'native-frozen':
                new['command'].append('--buffer-agglomeration')
            rows.append(new)
    return manifest, plan, env, rows


class ScreenTests(unittest.TestCase):
    def test_multiple_native_binaries_and_per_method_flags(self):
        data = multi_binary_fixture()
        report = analyze(*data)
        self.assertEqual(report['rows'], 20)
        self.assertEqual(report['full']['native_only'], 0)
        self.assertEqual(report['full']['definitive_by_method'],
                         {'native-frozen':1, 'native-buffer':1, 'native-batched':1, 'smpt':2, 'verifypn':1})
        plan, env, rows = data[1:]
        for key in ('target_zero_trap_methods', 'target_path_potential_methods', 'geometric_branches_methods'):
            plan[key] = ['native-batched']
            env[key] = ['native-batched']
        for row in rows:
            if row['method'] == 'native-batched':
                row['command'] = row['command'][:-1] + [
                    '--target-zero-trap', '--target-path-potential', '--buffer-agglomeration', '--geometric-branches']
        self.assertEqual(analyze(*data)['validity'], 'complete_consistent_screen')

    def test_native_registration_mismatches_rejected(self):
        for change in ('missing-method', 'extra-method', 'wrong-hash', 'wrong-binary', 'wrong-engine',
                       'relative-binary', 'path-alias', 'conflicting-hashes', 'missing-primary',
                       'wrong-primary-hash', 'unregistered-environment-flag', 'missing-environment-flag',
                       'duplicate-flag-label', 'external-flag-label', 'unknown-flag-label', 'null-flags'):
            data = multi_binary_fixture()
            plan, env = data[1:3]
            if change == 'missing-method': del plan['native_tools']['native-frozen']
            if change == 'extra-method': plan['native_tools']['native-other'] = copy.deepcopy(plan['native_tools']['native-frozen'])
            if change == 'wrong-hash': env['native_tools']['native-frozen']['binary_sha256'] = 'new-binary'
            if change == 'wrong-binary': env['native_tools']['native-frozen']['binary'] = plan['native_tools']['native-buffer']['binary']
            if change == 'wrong-engine': env['native_tools']['native-buffer']['engine'] = 'portfolio-batched'
            if change in ('relative-binary', 'path-alias'):
                path = 'results/frozen/vass-reach' if change == 'relative-binary' else '/workspace/pvass/./results/frozen/vass-reach'
                plan['native_tools']['native-frozen']['binary'] = env['native_tools']['native-frozen']['binary'] = path
            if change == 'conflicting-hashes':
                plan['native_tools']['native-buffer']['binary_sha256'] = env['native_tools']['native-buffer']['binary_sha256'] = 'other'
            if change == 'missing-primary': plan['native_binary'] = 'results/missing/vass-reach'
            if change == 'wrong-primary-hash': env['binary_sha256'] = 'binary'
            if change == 'unregistered-environment-flag': env['geometric_branches_methods'] = ['native-frozen']
            if change == 'missing-environment-flag': del env['buffer_agglomeration_methods']
            if change == 'duplicate-flag-label': plan['buffer_agglomeration_methods'] = ['native-buffer','native-buffer']
            if change == 'external-flag-label': plan['buffer_agglomeration_methods'] = ['smpt']
            if change == 'unknown-flag-label': plan['buffer_agglomeration_methods'] = ['native-other']
            if change == 'null-flags': plan['buffer_agglomeration_methods'] = None
            with self.subTest(change=change), self.assertRaises(ValueError):
                analyze(*data)

    def test_exact_native_commands_reject_extra_missing_or_changed_options(self):
        for change in ('binary', 'engine', 'seconds', 'states', 'property', 'pnml', 'xml',
                       'extra-option', 'extra-flag', 'missing-flag', 'duplicate-flag', 'duplicate-option', 'reordered', 'missing-command'):
            data = multi_binary_fixture()
            row = next(r for r in data[3] if r['method'] == 'native-batched')
            indices = {'binary':0, 'pnml':2, 'xml':4, 'property':6, 'engine':8, 'seconds':10, 'states':12}
            if change in indices: row['command'][indices[change]] = 'wrong'
            if change == 'extra-option': row['command'] += ['--max-states','1']
            if change == 'extra-flag': row['command'].append('--geometric-branches')
            if change == 'missing-flag': row['command'].pop()
            if change == 'duplicate-flag': row['command'].append('--buffer-agglomeration')
            if change == 'duplicate-option': row['command'] += ['--seconds','5.0']
            if change == 'reordered': row['command'][1:5] = row['command'][3:5] + row['command'][1:3]
            if change == 'missing-command': del row['command']
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'Exact native command'):
                analyze(*data)

    def test_legacy_native_binary_path_cannot_change_with_equal_hash(self):
        data = fixture()
        data[2]['native_tools']['native-focused']['binary'] = '/workspace/pvass/results/other/vass-reach'
        with self.assertRaises(ValueError):
            analyze(*data)

    def test_full_combined_denominator_retains_unavailable_slots(self):
        manifest, plan, env, original = multi_binary_fixture()
        query = manifest['queries'][0]
        prototypes = {r['method']:r for r in original if r['query'] == query['name']}
        queries, rows = [], []
        for i in range(656):
            item = copy.deepcopy(query)
            item['name'] = f'q{i}'
            item['branches'] = [dict(sha256=str(i))]
            if i >= 640:
                item['status'] = 'unsupported'
                item.pop('branches')
            queries.append(item)
            for method in plan['methods']:
                row = copy.deepcopy(prototypes[method])
                row.update(query=item['name'], verdict='unknown')
                if i >= 640:
                    row.update(verdict='unsupported', execution_attempted=False, failure_stage='collection',
                               command=[], branches=[], validation=None)
                rows.append(row)
        plan.update(properties=656, expected_rows=3280)
        env['property_order'] = [q['name'] for q in queries]
        report = analyze(dict(queries=queries), plan, env, rows)
        self.assertEqual(report['rows'], 3280)
        self.assertEqual(report['full']['properties'], 656)
        self.assertEqual(report['full']['collection_unavailable'], 16)
        self.assertEqual(report['imported']['properties'], 640)
        self.assertEqual(report['exact_ordered_branch_representatives'], 640)
        self.assertEqual(len(report['selections']['all_unresolved']), 640)

    def test_collection_failures_keep_denominator_without_becoming_hard_cases(self):
        data = fixture()
        failed = data[0]['queries'][2]
        failed['status'] = 'unsupported'
        failed.pop('kind')
        failed.pop('branches')
        for row in data[3]:
            if row['query'] == failed['name']:
                row.update(verdict='unsupported', execution_attempted=False,
                           failure_stage='collection', resources=None, branches=[], validation=None)
        report = analyze(*data)
        self.assertEqual(report['properties'], 4)
        self.assertEqual(report['full']['collection_unavailable'], 1)
        self.assertEqual(report['imported']['properties'], 3)
        self.assertEqual(report['exact_ordered_branch_representatives'], 3)
        self.assertEqual(report['selections']['collection_unavailable'], ['none'])
        self.assertEqual(report['selections']['all_unresolved'], ['none-copy'])
        self.assertFalse(report['has_invalid_answers'])
        case = next(c for c in report['cases'] if c['query'] == 'none')
        self.assertEqual(case['classification'], 'collection_unavailable')
        self.assertIsNone(case['representative'])
        self.assertIn('collection_failure', case['flags'])
        self.assertNotIn('capability_failure', case['flags'])
        self.assertEqual(report['runs'], data[3])

    def test_definitive_answer_for_unavailable_input_is_quarantined(self):
        data = fixture()
        data[0]['queries'][0].update(status='unsupported')
        data[0]['queries'][0].pop('branches')
        report = analyze(*data)
        self.assertTrue(report['has_invalid_answers'])
        self.assertFalse(report['cases'][0]['definitive_methods'])
        self.assertEqual(report['cases'][0]['classification'], 'collection_unavailable')
        self.assertNotIn('all', report['selections']['all_unresolved'])

    def test_classification_and_duplicates(self):
        report = analyze(*fixture())
        self.assertEqual(report['properties'],4)
        self.assertEqual(report['exact_ordered_branch_representatives'],3)
        self.assertEqual(report['full']['classifications'],dict(all_methods_definitive=1,mixed_solved_unresolved=1,no_method_definitive=2))
        self.assertEqual(report['full']['competitor_only'],1)
        self.assertEqual(report['families']['B']['full']['properties'],2)
        self.assertEqual(report['families']['B']['representatives']['properties'],1)
        self.assertEqual(report['selections']['all_unresolved'],['none','none-copy'])
        self.assertFalse(report['has_conflicts'])
        self.assertEqual(report['validity'],'complete_consistent_screen')

    def test_complete_matrix_required(self):
        for change in ('missing','duplicate','extra','bad_repeat'):
            data = fixture()
            rows = data[3]
            if change=='missing': rows.pop()
            if change=='duplicate': rows.append(copy.deepcopy(rows[0]))
            if change=='extra': rows.append(dict(rows[0],method='unexpected'))
            if change=='bad_repeat': rows[0]['repeat']=False
            with self.subTest(change=change), self.assertRaises(ValueError): analyze(*data)

    def test_external_disagreement_preserved(self):
        data = fixture()
        data[3][1]['verdict']='unreachable'
        report = analyze(*data)
        self.assertTrue(report['cases'][0]['disagreement'])
        self.assertEqual(report['full']['disagreements'],1)
        self.assertEqual(report['runs'],data[3])
        self.assertTrue(report['has_conflicts'])
        self.assertEqual(report['validity'],'requires_investigation')

    def test_definitive_failure_rows_are_not_solved(self):
        failures = [dict(outer_timeout=True), dict(deadline_exceeded=True),
                    dict(resources=dict(memory_limit_exceeded=True)), dict(error='error'),
                    dict(execution_attempted=False), dict(capability_failures=['backend']),
                    dict(validation=dict(exit_code=1)), dict(validation=dict(error='checker')),
                    dict(validation=dict(outer_timeout=True)), dict(exit_code=2)]
        for failure in failures:
            for index in (0,1):
                data=fixture()
                data[3][index].update(failure)
                with self.subTest(failure=failure,index=index):
                    report=analyze(*data)
                    self.assertIn('inconsistent_definitive_answer',report['row_flags'][index])
                    self.assertNotIn(data[3][index]['method'],report['cases'][0]['definitive_methods'])
                    self.assertEqual(report['runs'][index]['verdict'],'reachable')
                    self.assertTrue(report['has_invalid_answers'])
                    self.assertEqual(report['validity'],'requires_investigation')

    def test_failures_retained_and_not_called_clean_hard(self):
        data=fixture()
        data[3][6].update(verdict='error',error='checker failed',failure_stage='validation',
                          validation=dict(outer_timeout=True,resources=dict(memory_limit_exceeded=True)))
        data[3][7].update(capability_failures=['missing backend'],resources=dict(memory_limit_exceeded=True))
        data[3][8].update(outer_timeout=True)
        report=analyze(*data)
        flags=set(report['cases'][2]['flags'])
        self.assertTrue({'error','capability_failure','memory_limit','timeout','validation_timeout','validation_memory_limit','failure_stage:validation'} <= flags)
        self.assertEqual(report['runs'],data[3])
        self.assertEqual(report['selections']['all_unresolved'],['none','none-copy'])
        self.assertEqual(report['selections']['all_unresolved_without_observed_failures'],['none-copy'])

    def test_unchecked_native_answer_is_unresolved(self):
        data=fixture()
        data[3][0]['translation_check']='none'
        report=analyze(*data)
        self.assertIn('unchecked_native_answer',report['row_flags'][0])
        self.assertEqual(report['cases'][0]['classification'],'mixed_solved_unresolved')
        self.assertNotIn('native-focused',report['cases'][0]['definitive_methods'])

    def test_negative_requires_all_branches(self):
        data=fixture()
        data[0]['queries'][0]['branches'].append(dict(sha256='second'))
        row=data[3][0]
        row['verdict']='unreachable'
        row['branches']=[dict(branch=0,verdict='unreachable',independent_check='python-proof')]
        self.assertIn('unchecked_native_answer',analyze(*data)['row_flags'][0])
        row['branches'].append(dict(branch=1,verdict='unreachable',independent_check='python-proof'))
        self.assertNotIn('unchecked_native_answer',analyze(*data)['row_flags'][0])

    def test_duplicate_conflicts_and_polarity(self):
        data=fixture()
        data[0]['queries'][3]['kind']='AG'
        data[3][7]['verdict']='reachable'
        data[3][10]['verdict']='unreachable'
        report=analyze(*data)
        self.assertTrue(report['duplicate_groups'][0]['mixed_property_kinds'])
        self.assertTrue(report['duplicate_groups'][0]['disagreement'])
        self.assertEqual(report['full']['duplicate_disagreements'],2)

    def test_ordered_branches(self):
        manifest=fixture()[0]
        manifest['queries'][2]['branches']=[dict(sha256='x'),dict(sha256='y')]
        manifest['queries'][3]['branches']=[dict(sha256='y'),dict(sha256='x')]
        self.assertEqual(len(corpus_groups(manifest)),4)

    def test_plan_environment_mismatches(self):
        for change in ('seconds','validation','native','methods','properties','denominator',
                       'smpt','vp-binary','vp-commit','vp-config','validation-disabled'):
            data=fixture()
            env=data[2]
            if change=='seconds': env['seconds']=60
            if change=='validation': env['bounded_validation']['response_mib']=1
            if change=='native': env['native_tools']['native-focused']['binary_sha256']='other'
            if change=='methods': env['methods'].append('smpt')
            if change=='properties': env['property_order'].pop()
            if change=='denominator': data[1]['expected_rows']=11
            if change=='smpt': env['smpt_configurations']['smpt']=['WALK']
            if change=='vp-binary': env['verifypn']['binary_sha256']='other'
            if change=='vp-commit': env['verifypn']['source_commit']='other'
            if change=='vp-config': env['verifypn']['configurations']['verifypn']=['--trace']
            if change=='validation-disabled': env['bounded_validation']['enabled']=False
            with self.subTest(change=change), self.assertRaises(ValueError): analyze(*data)

    def test_registered_corpus_denominators(self):
        root=Path(__file__).resolve().parent.parent
        manifest=json.loads((root/'benchmarks/application-expansion-v1/manifest.json').read_text())
        groups=corpus_groups(manifest)
        self.assertEqual(len(manifest['queries']),192)
        self.assertEqual(len(groups),187)
        by_name={q['name']:q['family'] for q in manifest['queries']}
        counts={f:sum(by_name[g[0]]==f for g in groups) for f in set(by_name.values())}
        self.assertEqual(counts,dict(BART=32,CircadianClock=30,IOTPpurchase=32,NoC3x3=32,RobotManipulation=29,SmallOperatingSystem=32))


if __name__=='__main__':
    unittest.main()
