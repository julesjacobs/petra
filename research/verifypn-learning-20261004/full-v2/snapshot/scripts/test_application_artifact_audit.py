"""Synthetic local artifact fixtures; never execute a solver or contact a host."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]/'research/audit-linux-application-expansion-v1.py'
spec = importlib.util.spec_from_file_location('application_audit', SOURCE)
auditor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auditor)


def put(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value)+'\n')


def fixture(root, properties=192):
    corpus = root/'benchmarks/application-expansion-v1'
    results = root/'results/linux-application-expansion-v1'
    results.mkdir(parents=True)
    corpus.mkdir(parents=True)
    (corpus/'input').write_text('fixture input')
    digest=auditor.sha(corpus/'input')
    queries=[]
    for i in range(properties):
        queries.append(dict(name=f'q{i:03}', family=f'family{i//32}',suite='development',kind='EF',status='imported',observed=True,property_slot=i%16,
                            property_id=f'property{i}',branches=[dict(path='input',sha256=digest if i<6 else str(i))],
                            **{k:'input' for k in ('net','property','pnml','xml')},**{k+'_sha256':digest for k in ('net','property','pnml','xml')}))
    # Distinct branch bytes except the six identical queries (five duplicates).
    for i,q in enumerate(queries):
        if i>=6:
            p=corpus/f'branch{i}'
            p.write_text(str(i))
            q['branches']=[dict(path=p.name,sha256=auditor.sha(p))]
    put(corpus/'manifest.json',dict(queries=queries))
    binary=root/'results/frozen/vass-reach';binary.parent.mkdir();binary.write_text('frozen fixture')
    runner=results/'runner-source/runner.py';runner.parent.mkdir();runner.write_text('frozen runner fixture')
    methods={'native-focused':'portfolio-focused','native-symbolic':'portfolio-symbolic','smpt-full-portable':'full portable','verifypn-default':'default'}
    plan=dict(corpus=str(corpus.relative_to(root)),output=str(results.relative_to(root)),methods=methods,properties=properties,expected_rows=properties*len(methods),
              seconds=5,repeat=1,max_states=2000000,memory_mib=2048,outer_grace=0,order_seed=7,linux_cpus=[8],perf=True,
              native_binary=str(binary.relative_to(root)),native_binary_sha256=auditor.sha(binary),manifest_sha256=auditor.sha(corpus/'manifest.json'),
              validation=dict(seconds=60,memory_mib=2048,response_mib=64,dag_check_max_work=200000000,included_in_solver_timing=False),
              selection_evidence={},required_file_sha256={'scripts/runner.py':auditor.sha(runner),str(binary.relative_to(root)):auditor.sha(binary)},
              smpt_configurations={'smpt-full-portable':['WALK','SMT']},
              verifypn=dict(binary=auditor.REMOTE+'vendor/verifypn',binary_sha256='vp',source_commit='commit',source_status='',configurations={'verifypn-default':[]}))
    plan_path=root/'research/application-expansion-v1-screen-plan.json';put(plan_path,plan)
    order=[q['name'] for q in queries];random.Random(7).shuffle(order)
    env={k:copy.deepcopy(plan[k]) for k in ('seconds','repeat','max_states','memory_mib','outer_grace','order_seed','linux_cpus','perf','manifest_sha256','smpt_configurations','verifypn')}
    env.update(queries=properties,methods=list(methods),property_order=order,binary_sha256=plan['native_binary_sha256'],
               bounded_validation=dict(enabled=True,**plan['validation']),rust_original=True,track_resources=True,native_original=False,smpt_original=True,rust_original_methods=[],
               collection_counts=dict(planned=properties,imported=properties,unsupported=0,explicitly_unobserved=0),
               input_preflight=dict(mode='streaming-deduplicated-sha256',unique_files=1+max(0,properties-6),bytes_hashed=sum(p.stat().st_size for p in corpus.iterdir() if p.name!='manifest.json')),
               native_tools={m:dict(engine=methods[m],binary=auditor.REMOTE+plan['native_binary'],binary_sha256=plan['native_binary_sha256']) for m in methods if m.startswith('native-')},
               script_sha256={'runner.py':auditor.sha(runner)})
    put(results/'environment.json',env)
    rows=[]
    by_name={q['name']:q for q in queries}
    for index,name in enumerate(order):
        q=by_name[name];method_order=list(methods);offset=index%4
        for method in method_order[offset:]+method_order[:offset]:
            native=method.startswith('native-');prefix=f'{name}.{method}.0'
            pnml=auditor.REMOTE+plan['corpus']+'/input'
            if native:
                command=[auditor.REMOTE+plan['native_binary'],'--pnml',pnml,'--xml',pnml,'--property-id',q['property_id'],'--method',methods[method],'--seconds','5.0','--max-states','2000000']
            elif method=='smpt-full-portable':
                command=[auditor.REMOTE+'vendor/venv/bin/python','-m','smpt','-n',pnml,'--xml',pnml,'--methods','WALK','SMT','--timeout','5','--show-time','--show-techniques','--show-model','--export-proof',auditor.REMOTE+plan['output']+'/'+prefix+'.proof','--auto-reduce']
            else:
                command=[auditor.REMOTE+'vendor/verifypn','-x','1',pnml,pnml]
            state=dict(Result='timeout',CPUUsageNSec='1000000000',MemoryPeak='1000')
            row=dict(query=name,method=method,repeat=0,verdict='unknown',property_truth=None,property_kind='EF',suite='development',
                     collection_status='imported',collection_observed=True,property_slot=q['property_slot'],execution_attempted=True,
                     input_mode='rust-original-v1' if native else 'smpt-original' if method=='smpt-full-portable' else 'verifypn-original',
                     command=command,outer_timeout=True,exit_code=130,wall_seconds=5.01,
                     resources=dict(runner='linux-systemd-user',cpus=[8],memory_limit_bytes=2048*1024**2,perf_enabled=True,perf_counters=None,
                                    perf_failure='interrupted',systemd_result='timeout',systemd_properties=state,memory_limit_exceeded=False,cpu_seconds=1.0,peak_memory_bytes=1000))
            if method=='smpt-full-portable':row['enabled_methods']=['WALK','SMT']
            rows.append(row)
            log=results/(prefix+('.rust-original.json' if native else '.log'));log.write_text('partial output')
            put(Path(str(log)+'.systemd.json'),state)
            Path(str(log)+'.perf.csv').write_text('# interrupted\n')
    (results/'runs.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    return plan_path,results,rows


def multi_binary_fixture(root):
    plan_path, results, original = fixture(root, properties=4)
    plan = json.loads(plan_path.read_text())
    env = json.loads((results/'environment.json').read_text())
    new_binary = root/'results/new/vass-reach'
    new_binary.parent.mkdir()
    new_binary.write_text('new frozen fixture')
    old_binary = plan['native_binary']
    old_hash = plan['native_binary_sha256']
    plan.update(native_binary=str(new_binary.relative_to(root)), native_binary_sha256=auditor.sha(new_binary),
                methods={'native-frozen':'portfolio-focused', 'native-buffer':'portfolio-focused',
                         'native-batched':'portfolio-batched', 'smpt-full-portable':'full portable', 'verifypn-default':'default'},
                expected_rows=20, buffer_agglomeration_methods=['native-buffer','native-batched'])
    plan['native_tools'] = {
        method:dict(engine=engine,
                    binary=auditor.REMOTE+(old_binary if method=='native-frozen' else plan['native_binary']),
                    binary_sha256=old_hash if method=='native-frozen' else plan['native_binary_sha256'])
        for method,engine in plan['methods'].items() if method.startswith('native-')}
    plan['required_file_sha256'][plan['native_binary']] = plan['native_binary_sha256']
    adapter = results/'runner-source/kreach_adapter.py'
    adapter.write_text('frozen adapter fixture')
    plan['required_file_sha256']['scripts/kreach_adapter.py'] = auditor.sha(adapter)
    env.update(methods=list(plan['methods']), native_tools=copy.deepcopy(plan['native_tools']),
               binary_sha256=plan['native_binary_sha256'], buffer_agglomeration_methods=['native-buffer','native-batched'])
    env['script_sha256']['kreach_adapter.py'] = auditor.sha(adapter)
    rows=[]
    by_key={(r['query'],r['method']):r for r in original}
    for index,name in enumerate(env['property_order']):
        methods=env['methods'];offset=index%len(methods)
        for method in methods[offset:]+methods[:offset]:
            native=method.startswith('native-')
            row=copy.deepcopy(by_key[name,'native-focused' if native else method])
            source_prefix=f'{name}.{row["method"]}.0'
            row['method']=method
            if native:
                row['command'][0]=plan['native_tools'][method]['binary']
                row['command'][8]=plan['methods'][method]
                if method!='native-frozen':row['command'].append('--buffer-agglomeration')
                for suffix in ('.rust-original.json','.rust-original.json.systemd.json','.rust-original.json.perf.csv'):
                    (results/(f'{name}.{method}.0'+suffix)).write_bytes((results/(source_prefix+suffix)).read_bytes())
            rows.append(row)
    put(plan_path,plan)
    put(results/'environment.json',env)
    (results/'runs.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    return plan_path,results,rows


class ArtifactAuditTests(unittest.TestCase):
    def test_multiple_native_binaries_registered_flags_and_runner_snapshots(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);plan_path,results,rows=multi_binary_fixture(root)
            report=auditor.safe_audit(root,plan_path,results)
            self.assertEqual(report['audit_issues'],[])
            self.assertEqual(report['rows'],20)
            self.assertEqual(report['classification']['full']['properties'],4)
            self.assertEqual(set(report['classification']['full']['definitive_by_method']),
                             {'native-frozen','native-buffer','native-batched','smpt-full-portable','verifypn-default'})
            (root/'results/frozen/vass-reach').write_text('altered predecessor')
            self.assertTrue(any('Identity differs' in s for s in auditor.safe_audit(root,plan_path,results)['audit_issues']))

    def test_multiple_native_commands_and_flag_registration_cannot_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);plan_path,results,rows=multi_binary_fixture(root)
            original=copy.deepcopy(rows)
            for change in ('wrong-binary','wrong-engine','extra-flag','missing-flag','duplicate-option'):
                rows=copy.deepcopy(original)
                row=next(r for r in rows if r['method']=='native-batched')
                if change=='wrong-binary':row['command'][0]=auditor.REMOTE+'results/frozen/vass-reach'
                if change=='wrong-engine':row['command'][8]='portfolio-focused'
                if change=='extra-flag':row['command'].append('--geometric-branches')
                if change=='missing-flag':row['command'].pop()
                if change=='duplicate-option':row['command']+=['--seconds','5.0']
                (results/'runs.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
                with self.subTest(change=change):
                    report=auditor.safe_audit(root,plan_path,results)
                    self.assertEqual(len(report['full_rows']),20)
                    self.assertTrue(any('exact native command differs' in s for s in report['audit_issues']))
            (results/'runs.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in original))
            env=json.loads((results/'environment.json').read_text())
            env['geometric_branches_methods']=['native-batched'];put(results/'environment.json',env)
            self.assertTrue(any('native flag methods differ' in s for s in auditor.safe_audit(root,plan_path,results)['audit_issues']))

    def test_every_explicit_native_binary_and_runtime_snapshot_must_be_pinned(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);plan_path,results,_=multi_binary_fixture(root)
            original=json.loads(plan_path.read_text())
            for missing in ('results/frozen/vass-reach','scripts/kreach_adapter.py'):
                plan=copy.deepcopy(original);del plan['required_file_sha256'][missing];put(plan_path,plan)
                with self.subTest(missing=missing):
                    report=auditor.safe_audit(root,plan_path,results)
                    self.assertEqual(report['status'],'failed')
                    self.assertTrue(any('registered file identities' in s for s in report['audit_issues']))
            put(plan_path,original)
            (results/'runner-source/kreach_adapter.py').unlink()
            self.assertTrue(any('Missing identity evidence' in s for s in auditor.safe_audit(root,plan_path,results)['audit_issues']))

    def test_unavailable_collection_has_no_solver_or_counter_requirements(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);plan_path,results,rows=fixture(root)
            plan=json.loads(plan_path.read_text())
            corpus=root/plan['corpus'];manifest=json.loads((corpus/'manifest.json').read_text())
            query=manifest['queries'][0]
            name=query['name']
            manifest['queries'][0]={k:query[k] for k in ('name','family','suite','property_slot')}
            manifest['queries'][0].update(status='unsupported',observed=False,error='collection limit')
            put(corpus/'manifest.json',manifest)
            plan['manifest_sha256']=auditor.sha(corpus/'manifest.json');put(plan_path,plan)
            environment=json.loads((results/'environment.json').read_text())
            environment['manifest_sha256']=plan['manifest_sha256']
            environment['collection_counts']=dict(planned=192,imported=191,unsupported=1,explicitly_unobserved=1)
            put(results/'environment.json',environment)
            for i,row in enumerate(rows):
                if row['query']==name:
                    rows[i]={k:row[k] for k in ('query','method','repeat','suite','property_slot','input_mode')}
                    rows[i].update(verdict='unsupported',property_kind=None,property_truth=None,
                                   collection_status='unsupported',collection_observed=False,
                                   execution_attempted=False,failure_stage='collection',resources=None,
                                   error='collection limit',branches=[],independent_checks=[])
            (results/'runs.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
            report=auditor.safe_audit(root,plan_path,results)
            self.assertEqual(report['audit_issues'],[])
            self.assertEqual(report['classification']['full']['collection_unavailable'],1)
            self.assertEqual(sum(r.get('collection_unavailable',False) for r in report['row_audits']),4)

    def test_complete_and_missing_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);plan,results,rows=fixture(root)
            report=auditor.safe_audit(root,plan,results)
            self.assertEqual(report['audit_issues'],[])
            self.assertEqual(report['status'],'passed')
            self.assertEqual(report['exact_ordered_branch_representatives'],187)
            self.assertEqual(len(report['full_rows']),768)
            self.assertEqual(len(report['failures']),768)
            self.assertEqual(report['classification']['full']['classifications']['no_method_definitive'],192)
            next(results.glob('*.systemd.json')).unlink()
            report=auditor.safe_audit(root,plan,results)
            self.assertEqual(report['status'],'failed')
            self.assertTrue(any('missing captured artifact' in x for x in report['audit_issues']))

    def test_missing_null_partial_and_duplicate_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);plan,results,rows=fixture(root)
            for contents in ('',json.dumps(rows[0])+'\n',json.dumps(rows[0])+'\n'+json.dumps(rows[0])+'\n','null\n{partial\n'):
                (results/'runs.jsonl').write_text(contents)
                report=auditor.safe_audit(root,plan,results)
                self.assertEqual(report['status'],'failed')
                self.assertEqual(report['expected_rows'],768)
                self.assertEqual(len(report['full_rows']),0 if contents in ('','null\n{partial\n') else contents.count('\n'))
                if contents.startswith('null'):self.assertEqual(len(report['invalid_rows']),2)
            put(results/'environment.json',None)
            report=auditor.safe_audit(root,plan,results)
            self.assertEqual(report['status'],'failed')
            (results/'environment.json').unlink()
            self.assertEqual(auditor.safe_audit(root,plan,results)['status'],'failed')

    def test_perf_null_partial_and_exact_decode(self):
        self.assertEqual(auditor.perf_status({'perf_counters':None},'instructions:u'),'missing-or-invalid-value')
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'perf.csv'
            path.write_text('17;;instructions:u;12;50.00;;\n')
            counters,issues=auditor.parse_perf(path)
            self.assertEqual(issues,[])
            self.assertEqual(auditor.perf_status({'perf_counters':counters},'instructions:u'),'multiplexed')
            self.assertEqual(auditor.perf_status({'perf_counters':counters},'cycles:u'),'missing-or-invalid-value')
            path.write_text('<not counted>;;instructions:u;0;0;;\n')
            counters,issues=auditor.parse_perf(path)
            self.assertFalse(counters)
            self.assertTrue(issues)

    def test_saved_native_validation_external_formula_and_runner_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);plan_path,results,rows=fixture(root)
            plan=json.loads(plan_path.read_text())
            queries={q['name']:q for q in json.loads((root/plan['corpus']/'manifest.json').read_text())['queries']}
            def save_rows():
                (results/'runs.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
            def success(row):
                row.update(verdict='reachable',property_truth=True,outer_timeout=False,exit_code=0,wall_seconds=1.0)
                native=row['method'].startswith('native-')
                log=results/(f"{row['query']}.{row['method']}.0"+('.rust-original.json' if native else '.log'))
                state=row['resources']['systemd_properties'];state['Result']='success'
                row['resources'].update(systemd_result='success',perf_failure=None)
                put(Path(str(log)+'.systemd.json'),state)
                perf=Path(str(log)+'.perf.csv')
                perf.write_text('17;;instructions:u;12;100.00;;\n20;;cycles:u;12;100.00;;\n1;msec;task-clock:u;12;100.00;;\n')
                row['resources']['perf_counters']=auditor.parse_perf(perf)[0]
                return log
            native=next(r for r in rows if r['method']=='native-focused')
            log=success(native);query=queries[native['query']]
            response=dict(verdict='reachable',property_truth=True,branches=[dict(branch=0,verdict='reachable',independent_check='python-witness')],
                          independent_checks=['python-witness'],translation_check='independent-original-input-equals-all-canonical-branches')
            native.update(response)
            native['validation']=dict(exit_code=0,outer_timeout=False,resources=dict(memory_limit_exceeded=False),
                seconds_limit=60,memory_limit_bytes=2048*1024**2,response_limit_bytes=64*1024**2,dag_check_max_work=200000000,included_in_solver_timing=False)
            put(log,dict(verdict='reachable',property_id=query['property_id'],property_kind='EF',branch_count=1,deadline_exceeded=False))
            put(Path(str(log)+'.validation-request.json'),dict(query=query,corpus=auditor.REMOTE+plan['corpus'],artifacts=auditor.REMOTE+plan['output'],
                log=auditor.REMOTE+plan['output']+'/'+log.name,mode='rust-original-v1',exit_code=0,outer_timeout=False,
                memory_bytes=2048*1024**2,response_bytes=64*1024**2,dag_check_max_work=200000000))
            response_path=Path(str(log)+'.validation-response.json');put(response_path,response)
            Path(str(log)+'.validation.log').write_text('')
            external=next(r for r in rows if r['method']=='smpt-full-portable')
            external_log=success(external)
            external['formula_output']='FORMULA '+queries[external['query']]['property_id']+' TRUE TECHNIQUES WALK'
            external_log.write_text(external['formula_output']+'\n')
            save_rows()
            report=auditor.safe_audit(root,plan_path,results)
            self.assertEqual(report['audit_issues'],[])
            for invalid in (None,{},dict(response,verdict='unreachable')):
                put(response_path,invalid)
                report=auditor.safe_audit(root,plan_path,results)
                self.assertEqual(report['status'],'failed')
                self.assertEqual(len(report['full_rows']),768)
            put(response_path,response)
            external_log.write_text('FORMULA '+queries[external['query']]['property_id']+' FALSE\n')
            self.assertTrue(any('formula output differs' in issue for issue in auditor.safe_audit(root,plan_path,results)['audit_issues']))
            (results/'runner-source/runner.py').write_text('modified')
            self.assertTrue(any('Identity differs' in issue for issue in auditor.safe_audit(root,plan_path,results)['audit_issues']))


if __name__=='__main__':unittest.main()
