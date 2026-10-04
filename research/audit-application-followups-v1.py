#!/usr/bin/env python3
"""Audit saved application follow-ups locally, without executing tools or proofs."""
import collections
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import re
import shlex
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from analyze_application_expansion import analyze, corpus_groups, native_checked, failure_flags
spec=importlib.util.spec_from_file_location('application_artifacts',ROOT/'research/audit-linux-application-expansion-v1.py')
helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)
REMOTE=helpers.REMOTE
DEFINITIVE={'reachable','unreachable'}


class Audit:
    def __init__(self):
        self.hashes={};self.issues=[];self.warnings=[];self.identities=[]
    def check(self,condition,message):
        if not condition:self.issues.append(message)
    def digest(self,path):
        path=Path(path).resolve();key=str(path.relative_to(ROOT))
        if key not in self.hashes:self.hashes[key]=helpers.sha(path)
        return self.hashes[key]
    def read(self,path):
        self.digest(path)
        return json.loads(Path(path).read_text())
    def rows(self,path):
        self.digest(path)
        return [json.loads(line) for line in Path(path).read_text().splitlines()]
    def text(self,path):
        self.digest(path)
        return Path(path).read_text(errors='replace')
    def identity(self,path,expected,scope):
        actual=self.digest(path)
        self.check(actual==expected,'Identity differs: '+str(path))
        self.identities.append(dict(path=str(Path(path).relative_to(ROOT)),expected=expected,actual=actual,scope=scope))
    def resources(self,row,log,seconds,plan):
        r=row['resources'];state=self.read(Path(str(log)+'.systemd.json'))
        self.check(state==r['systemd_properties'],f'{log.name}: systemd sidecar differs')
        for key,value in dict(runner='linux-systemd-user',cpus=plan['linux_cpus'],memory_limit_bytes=plan['memory_mib']*1024**2,perf_enabled=True,systemd_result=state['Result'],memory_limit_exceeded=state['Result']=='oom-kill').items():
            self.check(r.get(key)==value,f'{log.name}: resource {key} differs')
        for key,field,scale in [('CPUUsageNSec','cpu_seconds',1e9),('MemoryPeak','peak_memory_bytes',1)]:
            value=state.get(key)
            expected=None if value in (None,'','[not set]','infinity','18446744073709551615') else int(value)/scale
            self.check(r.get(field)==expected,f'{log.name}: accounting {field} differs')
        if state['Result'] in ('timeout','oom-kill'):self.check(row['outer_timeout'] is True,f'{log.name}: missing cgroup failure flag')
        path=Path(str(log)+'.perf.csv');parsed,problems=helpers.parse_perf(path);self.digest(path)
        counters=r.get('perf_counters') or {}
        if counters:self.check(not problems and counters==parsed,f'{log.name}: raw perf differs')
        else:self.check(bool(r.get('perf_failure')) and state['Result'] in ('timeout','oom-kill'),f'{log.name}: unexplained missing perf')
        if any(helpers.perf_status(r,event)!='full-coverage' for event in ('instructions:u','cycles:u','task-clock')):
            self.warnings.append(f'{log.name}: incomplete perf coverage retained')
        if row.get('verdict') in DEFINITIVE:
            self.check(not row['outer_timeout'] and not r['memory_limit_exceeded'] and row['wall_seconds']<=seconds,
                       f'{log.name}: definitive outside execution budget')
        self.digest(log)
    def validation(self,row,query,log,corpus,out,limits):
        self.digest(Path(str(log)+'.validation.log'))
        v=row['validation'];request=self.read(Path(str(log)+'.validation-request.json'))
        response=self.read(Path(str(log)+'.validation-response.json'))
        expected=dict(query=query,corpus=REMOTE+corpus,artifacts=REMOTE+out,log=REMOTE+out+'/'+log.name,mode='rust-original-v1',
                      outer_timeout=row['outer_timeout'],exit_code=row['exit_code'],memory_bytes=limits['memory_mib']*1024**2,
                      response_bytes=limits['response_mib']*1024**2,dag_check_max_work=limits.get('dag_check_max_work',limits.get('dag_max_work')))
        self.check(request==expected,f'{log.name}: validation request differs')
        for key,value in dict(seconds_limit=limits['seconds'],memory_limit_bytes=expected['memory_bytes'],response_limit_bytes=expected['response_bytes'],dag_check_max_work=expected['dag_check_max_work'],included_in_solver_timing=False).items():
            self.check(v.get(key)==value,f'{log.name}: validation {key} differs')
        self.check(v['exit_code']==0 and not v['outer_timeout'] and not v['resources']['memory_limit_exceeded'],f'{log.name}: validator did not complete')
        self.check(bool(response) and all(row.get(k)==value for k,value in response.items()),f'{log.name}: saved validator response differs')
        if row['verdict'] in DEFINITIVE:
            self.check(native_checked(row,query),f'{log.name}: missing checked native answer')
        raw=self.read(log)
        self.check(raw['verdict']==row['verdict'] and raw['property_truth']==row['property_truth'] and raw['property_id']==query['property_id'] and raw['property_kind']==query['kind'] and raw['branch_count']==len(query['branches']),f'{log.name}: native saved answer differs')
        self.check(raw['deadline_exceeded']==row.get('deadline_exceeded'),f'{log.name}: raw deadline differs')
        return raw


def audit():
    a=Audit()
    parent_plan=a.read(ROOT/'research/application-expansion-v1-screen-plan.json')
    parent_manifest=a.read(ROOT/parent_plan['corpus']/'manifest.json')
    parent_env=a.read(ROOT/parent_plan['output']/'environment.json')
    parent_rows=a.rows(ROOT/parent_plan['output']/'runs.jsonl')
    parent=analyze(parent_manifest,parent_plan,parent_env,parent_rows)
    parent_artifacts=a.read(ROOT/'research/linux-application-expansion-v1-verification.json')
    a.check(parent_artifacts['full_rows']==parent_rows and parent_artifacts['classification']==parent,'Parent audit source/classification differs')
    a.check(parent_artifacts['audit_issues']==['Classification reports conflicts or invalid definitive answers'],'Unexpected parent artifact issue')
    a.check(len(parent_rows)==768 and parent['properties']==192 and len(corpus_groups(parent_manifest))==187,'Parent denominator differs')
    selected=sorted(c['query'] for c in parent['cases'] if c['competitor_only'])
    raw_counts={m:sum(r['method']==m and r['verdict'] in DEFINITIVE for r in parent_rows) for m in parent_env['methods']}
    representatives={g[0] for g in corpus_groups(parent_manifest)}
    raw_representative_counts={m:sum(r['method']==m and r['verdict'] in DEFINITIVE and r['query'] in representatives for r in parent_rows) for m in parent_env['methods']}
    exceptions=collections.defaultdict(list);missing=collections.defaultdict(list);overlaps=collections.Counter()
    for i,row in enumerate(parent_rows):
        if row['method']!='smpt-full-portable':continue
        path=ROOT/parent_plan['output']/f"{row['query']}.{row['method']}.0.log"
        lines=a.text(path).splitlines()
        found=set(line for line in lines if re.match(r'^[A-Za-z_][A-Za-z0-9_.]*(?:Error|Exception)(?::|$)',line) or line.startswith('KeyboardInterrupt'))
        for line in found:exceptions[line].append(row['query'])
        for line in found:
            if 'No such file or directory' in line or 'not found' in line:missing[line].append(row['query'])
        overlaps[('definitive' if row['verdict'] in DEFINITIVE else 'unresolved',tuple(parent['row_flags'][i]))]+=1
    main_summary=dict(raw_definitive=raw_counts,raw_representative_definitive=raw_representative_counts,strict_definitive=parent['full']['definitive_by_method'],
        classifications=parent['full']['classifications'],representatives=parent['representatives'],families=parent['families'],
        has_verdict_conflicts=parent['has_conflicts'],strict_quarantined=parent['has_invalid_answers'],
        capability_exceptions=dict(missing),all_exceptions=dict(exceptions),flag_overlaps=[dict(outcome=k[0],flags=list(k[1]),rows=v) for k,v in overlaps.items()],
        interpretation='Reported definitive plus process/capability failures is excluded by the registered strict policy. This does not establish a false FORMULA answer. Missing minizinc blocks a full-capability SMPT comparison; other recorded exceptions are interruption or broken IPC, not another identified missing executable.')
    gp=a.read(ROOT/'research/application-gaps-v2-plan.json');gm=a.read(ROOT/gp['corpus']/'manifest.json')
    out=ROOT/gp['output'];env=a.read(out/'environment.json');rows=a.rows(out/'runs.jsonl');queries={q['name']:q for q in gm['queries']}
    a.check(selected==sorted(queries)==gp['selection_evidence']['selected'],'Gap selection differs from all parent competitor-only cases')
    a.check(gm['source_evidence']==gp['selection_evidence'] and gp['selection_evidence']['parent_queries']==192 and gp['selection_evidence']['parent_representatives']==187,'Gap parent provenance differs')
    for key,value in parent_plan['required_file_sha256'].items():a.check(gp['required_file_sha256'].get(key)==value,'Gap frozen registration changed: '+key)
    a.identity(ROOT/gp['corpus']/'manifest.json',gp['manifest_sha256'],'gap registered manifest')
    # Native binary/input bytes are local; remote tool/source identities remain reported metadata.
    recorded={'scripts/'+k:v for k,v in env['script_sha256'].items()}
    for tool in env['native_tools'].values():recorded[helpers.relative(tool['binary'])]=tool['binary_sha256']
    recorded[helpers.relative(env['verifypn']['binary'])]=env['verifypn']['binary_sha256']
    recorded[helpers.relative(env['native_python'])]=env['native_python_sha256']
    for tool in env.get('tools',{}).values():recorded[helpers.relative(tool['path'])]=tool['sha256']
    for name,digest in env['smpt_source_sha256'].items():recorded[helpers.relative(env['smpt_root']+'/'+name)]=digest
    for name,digest in gp['required_file_sha256'].items():
        if name.startswith('scripts/'):
            a.identity(out/'runner-source'/Path(name).name,digest,'fetched frozen runner bytes')
            a.check(recorded.get(name)==digest,'Recorded frozen runner differs: '+name)
        elif name.startswith('vendor/'):
            a.check(recorded.get(name)==digest,'Recorded remote tool/source differs: '+name)
            a.identities.append(dict(path=name,expected=digest,actual=recorded.get(name),scope='environment-reported remote identity'))
        else:a.identity(ROOT/name,digest,'local frozen bytes')
    for key in ('smpt_configurations','native_tools','verifypn','binary_sha256','bounded_validation','script_sha256','rust_original','smpt_original','rust_original_methods','native_original','track_resources','tools','smpt_source_sha256'):
        a.check(env.get(key)==parent_env.get(key),'Gap configuration changed from parent: '+key)
    for key in ('seconds','repeat','max_states','memory_mib','linux_cpus','perf','outer_grace','order_seed','manifest_sha256'):
        a.check(env.get(key)==gp[key],'Gap registered setting differs: '+key)
    order=list(queries);random.Random(gp['order_seed']).shuffle(order)
    a.check(env['property_order']==order and set(env['methods'])==set(gp['methods']),'Gap property/method order differs')
    expected_order=[]
    for index,name in enumerate(order):
        ms=env['methods'];offset=index%len(ms);expected_order.extend((name,m,0) for m in ms[offset:]+ms[:offset])
    a.check(len(rows)==gp['expected_rows']==12 and [(r['query'],r['method'],r['repeat']) for r in rows]==expected_order,'Gap matrix differs')
    original_queries={q['name']:q for q in parent_manifest['queries']}
    for q in queries.values():
        expected=dict(original_queries[q['name']])
        for key in list(expected):
            if key+'_sha256' in expected:expected[key]='../application-expansion-v1/'+expected[key]
        expected['branches']=[dict(b,path='../application-expansion-v1/'+b['path']) for b in expected['branches']]
        a.check(q==expected,'Gap relocation changed query: '+q['name'])
        for key in q:
            if key+'_sha256' in q:a.identity(ROOT/gp['corpus']/q[key],q[key+'_sha256'],'relocated original artifact')
    gap_cases=[]
    for row in rows:
        q=queries[row['query']];method=row['method'];native=method.startswith('native-')
        stem=f"{q['name']}.{method}.0";log=out/(stem+('.rust-original.json' if native else '.log'))
        pnml=REMOTE+gp['corpus']+'/'+q['pnml'];xml=REMOTE+gp['corpus']+'/'+q['xml']
        if native:
            command=[REMOTE+gp['native_binary'],'--pnml',pnml,'--xml',xml,'--property-id',q['property_id'],'--method',gp['methods'][method],'--seconds','60.0','--max-states','2000000']
        elif method=='smpt-full-portable':
            command=[env['smpt_python'],'-m','smpt','-n',pnml,'--xml',xml,'--methods',*env['smpt_configurations'][method],'--timeout','60','--show-time','--show-techniques','--show-model','--export-proof',REMOTE+gp['output']+'/'+stem+'.proof','--auto-reduce']
            a.check(row['enabled_methods']==env['smpt_configurations'][method],stem+': enabled SMPT modes differ')
        else:command=[env['verifypn']['binary'],'-x','1',pnml,xml]
        a.check(row['command']==command,stem+': command differs')
        a.check(row['property_kind']==q['kind'] and row['suite']==q['suite'] and row['property_slot']==q['property_slot'] and row['collection_status']=='imported' and row['execution_attempted'],stem+': query metadata differs')
        truth=(row['verdict']=='reachable')==(q['kind']=='EF') if row['verdict'] in DEFINITIVE else None
        a.check(row['property_truth'] is truth,stem+': property truth differs')
        a.resources(row,log,gp['seconds'],gp)
        if native:
            if 'validation' in row:a.validation(row,q,log,gp['corpus'],gp['output'],gp['validation'])
            else:a.check(row['verdict']=='unknown' and row['outer_timeout'],stem+': missing required validator')
        else:
            text=a.text(log);matches=re.findall(r'^FORMULA '+re.escape(q['property_id'])+r' (TRUE|FALSE)(?:\s|$)',text,re.M)
            if row['verdict'] in DEFINITIVE:a.check(set(matches)=={'TRUE' if truth else 'FALSE'},stem+': external formula mismatch')
            if method=='smpt-full-portable':
                flags=sorted(set(l for l in text.splitlines() if re.search(r'command not found|No such file or directory|bad command line|error: 4ti2 failed',l)))
                a.check(flags==row['capability_failures'] and ('Traceback (most recent call last):' in text)==row['subprocess_error'],stem+': external failure fields differ')
        gap_cases.append(dict(query=row['query'],method=method,verdict=row['verdict'],wall_seconds=row['wall_seconds'],flags=sorted(failure_flags(row)),instructions=(row['resources'].get('perf_counters') or {}).get('instructions:u',{}).get('value')))
    for name in queries:a.check(len({r['verdict'] for r in rows if r['query']==name}&DEFINITIVE)<=1,'Gap disagreement: '+name)
    v1=a.read(ROOT/'research/application-gaps-v1-plan.json');v1m=a.read(ROOT/v1['corpus']/'manifest.json');failure=a.text(ROOT/'research/linux-application-gaps-v1.log')
    a.identity(ROOT/v1['corpus']/'manifest.json',v1['manifest_sha256'],'retained failed-preflight manifest')
    a.check('preflight_inputs' in failure and 'FileNotFoundError' in failure and 'application-gaps-v1/NoC3x3-PT-8B__RC06/property.xml' in failure,'v1 failure cause differs')
    a.check((ROOT/v1['output']).is_dir() and not list((ROOT/v1['output']).iterdir()),'v1 output not retained empty')
    a.check({q['name'] for q in v1m['queries']}==set(queries),'v1 selection differs')
    for version in (1,2):a.text(ROOT/f'research/run-linux-application-gaps-v{version}.sh')
    a.text(ROOT/'research/linux-application-gaps-v2.log')
    dp=a.read(ROOT/'research/application-budget-diagnostic-v1-plan.json');dout=ROOT/dp['output'];denv=a.read(dout/'environment.json');dr=a.rows(dout/'runs.jsonl')
    a.check(a.read(dout/'plan.json')==dp==denv['plan'],'Diagnostic saved plan differs')
    for key,value in gp['required_file_sha256'].items():a.check(dp['required_file_sha256'].get(key)==value,'Diagnostic registration changed: '+key)
    runner='research/run-application-budget-diagnostic-v1.py'
    a.identity(ROOT/runner,dp['required_file_sha256'][runner],'registered diagnostic driver')
    a.identity(dout/Path(runner).name,dp['required_file_sha256'][runner],'saved diagnostic driver')
    a.check(a.read(dout/'completed.json')==dict(rows=6,frozen_inputs_unchanged=True),'Diagnostic completion marker differs')
    dorder=[(n,s) for n in dp['queries'] for s in dp['internal_seconds']];random.Random(dp['order_seed']).shuffle(dorder)
    a.check(denv['order']==[list(x) for x in dorder] and [(r['query'],r['seconds']) for r in dr]==dorder and len(dr)==6,'Diagnostic matrix/order differs')
    diagnostic=[]
    for row in dr:
        name,seconds=row['query'],row['seconds'];q=queries[name];stem=f'{name}.seconds-{seconds}';log=dout/(stem+'.rust-original.json');profile=dout/(stem+'.profile.jsonl')
        command=[REMOTE+dp['binary'],'--pnml',REMOTE+dp['corpus']+'/'+q['pnml'],'--xml',REMOTE+dp['corpus']+'/'+q['xml'],'--property-id',q['property_id'],'--method',dp['method'],'--seconds',str(seconds),'--max-states','2000000']
        a.check(row['command']==command,stem+': diagnostic command differs')
        wrapper='VASS_PORTFOLIO_PROFILE=1 VASS_RELAXED_PROFILE=1 exec '+shlex.join(command)+' 2>'+shlex.quote(REMOTE+dp['output']+'/'+profile.name)+'\n'
        a.check(a.text(dout/(stem+'.sh'))==wrapper,stem+': profiling wrapper differs')
        a.resources(row,log,seconds+dp['outer_grace'],dp)
        raw=a.validation(row,q,log,dp['corpus'],dp['output'],dp['validation'])
        events=[];other=[]
        for line in a.text(profile).splitlines():
            try:events.append(json.loads(line))
            except ValueError:other.append(line)
        a.check(events==row['events'] and other==row['other_profile_lines'],stem+': saved profile differs')
        pending=[]
        for event in events:
            if event.get('event')=='phase-start':pending.append(event['name'])
            if event.get('event')=='phase-end':
                a.check(bool(pending) and pending.pop()==event['name'],stem+': phase pairing differs')
                a.check(event['phase_seconds']>=0,stem+': negative phase time')
        a.check(not pending,stem+': incomplete profile phase')
        relaxed=[{k:e[k] for k in ('phase_seconds','verdict','states','reason')} for e in events if e.get('event')=='phase-end' and e.get('name')=='vass_reach::relaxed::solve_focused']
        diagnostic.append(dict(query=name,seconds=seconds,verdict=row['verdict'],wall_seconds=row['wall_seconds'],deadline_exceeded=row['deadline_exceeded'],outer_timeout=row['outer_timeout'],relaxed_phases=relaxed,branches=row['branches'],raw_attempts=[dict(branch=x['branch'],verdict=x['outcome']['verdict']) for x in raw['attempts']]))
    tp=a.read(ROOT/'research/noc3x3-verifypn-trace-v1-plan.json');tout=ROOT/'results/noc3x3-verifypn-trace-v1';tr=a.read(tout/'run.json')
    a.check(a.read(tout/'plan.json')==tp,'Trace plan differs')
    a.check(tp['query']==queries[tp['query']['name']] and tp['binary_sha256']==env['verifypn']['binary_sha256'],'Trace input/binary differs')
    q=tp['query'];a.check(tp['command']==[env['verifypn']['binary'],'-x','1','--trace',REMOTE+tp['corpus']+'/'+q['pnml'],REMOTE+tp['corpus']+'/'+q['xml']],'Trace command differs')
    a.resources(tr,tout/'trace.log',tp['seconds'],tp)
    trace_text=a.text(tout/'trace.log')
    a.check(tr['outer_timeout'] and tr['resources']['systemd_result']=='timeout','Trace terminal status differs')
    a.check(not re.search(r'^FORMULA ',trace_text,re.M),'Trace produced a formula requiring review')
    a.check('Rule H, J, R, S, Q disabled when a trace is requested.' in trace_text,'Trace restriction evidence absent')
    for folder in (out,dout,tout):
        for path in folder.rglob('*'):
            if path.is_file():a.digest(path)
    a.digest(Path(__file__))
    a.digest(ROOT/'scripts/analyze_application_expansion.py')
    a.digest(ROOT/'research/audit-linux-application-expansion-v1.py')
    return dict(status='passed' if not a.issues else 'failed',audit_issues=a.issues,warnings=a.warnings,
        parent=dict(properties=192,exact_ordered_branch_representatives=187,rows=768,artifact_audit_status=parent_artifacts['status'],coverage=main_summary),
        gaps=dict(properties=3,rows=12,cases=gap_cases,raw_definitive={m:sum(r['method']==m and r['verdict'] in DEFINITIVE for r in rows) for m in env['methods']},
                  strict_definitive={m:sum(r['method']==m and r['verdict'] in DEFINITIVE and not failure_flags(r) for r in rows) for m in env['methods']},full_rows=rows),
        failed_preflight=dict(version=1,solver_rows=0,scope='Saved preflight stack trace and empty output support failure before solver invocation; v1 manifest/plan/log retained. v2 relocates all top-level artifact paths paired with hashes.'),
        diagnostic=dict(rows=6,summary=diagnostic,full_rows=dr,scope='Profiling enabled, 2s outer grace. Separate budget-dependent scheduling diagnostic; never replace strict-screen timing.'),
        trace=dict(run=tr,scope='Trace mode timed out; no FORMULA or independently replayable witness obtained. Trace disables H/J/R/S/Q reductions, so this is not the default-mode performance result.'),
        identities=a.identities,sources=a.hashes,
        audit_scope='Saved-artifact consistency and independently checked native metadata, not fresh proof replay. Remote tool hashes are environment-reported. One-repeat outcome-selected development follow-ups. Parent capability-contaminated strict classification retained unchanged; no stable timing or solver-superiority claim.')


def main():
    output=ROOT/'research/application-followups-v1-verification.json'
    try:report=audit()
    except Exception as error:
        report=dict(status='failed',audit_issues=[f'{type(error).__name__}: {error}'],parent_properties=192,parent_representatives=187,
                    full_rows={str(p):[json.loads(x) for x in p.read_text().splitlines()] for p in [ROOT/'results/linux-application-gaps-v2/runs.jsonl',ROOT/'results/application-budget-diagnostic-v1/runs.jsonl']})
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],issues=report['audit_issues'],output=str(output)),indent=2))
    return int(report['status']!='passed')


if __name__=='__main__':sys.exit(main())
