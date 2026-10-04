import hashlib,json,os,random,shlex,shutil,sys
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from process_runner import workspace_workloads
from linux_runner import run
from bounded_validation import run_validation

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
plan_path=ROOT/'research/application-budget-diagnostic-v1-plan.json'
if '--register' in sys.argv:
    parent=json.loads((ROOT/'research/application-gaps-v2-plan.json').read_text())
    required=parent['required_file_sha256'].copy()
    required[str(Path(__file__).relative_to(ROOT))]=sha(__file__)
    plan=dict(status='registered before launch',corpus=parent['corpus'],queries=parent['selection_evidence']['selected'],expected_rows=6,internal_seconds=[5,60],outer_grace=2,method='portfolio-focused',max_states=2000000,memory_mib=2048,linux_cpus=[8],perf=True,order_seed=20261105,output='results/application-budget-diagnostic-v1',binary=parent['native_binary'],required_file_sha256=required,validation=dict(seconds=60,memory_mib=2048,response_mib=64,dag_max_work=200000000),scope='All3 application competitor-only queries, focused engine at5s/60s with profiling and2s diagnostic outer grace. Investigate budget-dependent scheduling; no timing substitution into strict screens. Parent192queries/187representatives; one repetition.')
    with plan_path.open('x') as f:json.dump(plan,f,indent=2);f.write('\n')
    print('Registered',sha(plan_path));sys.exit(0)
plan=json.loads(plan_path.read_text())
assert not workspace_workloads(ROOT)
for name,expected in plan['required_file_sha256'].items():assert sha(ROOT/name)==expected,name
out=ROOT/plan['output'];out.mkdir()
shutil.copyfile(plan_path,out/'plan.json')
shutil.copyfile(__file__,out/Path(__file__).name)
corpus=ROOT/plan['corpus'];queries={q['name']:q for q in json.loads((corpus/'manifest.json').read_text())['queries']}
args=SimpleNamespace(native_python=ROOT/'vendor/venv/bin/python',validation_seconds=60,validation_memory_mib=2048,validation_response_mib=64,validation_dag_work=200000000)
order=[(name,seconds) for name in plan['queries'] for seconds in plan['internal_seconds']]
random.Random(plan['order_seed']).shuffle(order)
(out/'environment.json').write_text(json.dumps(dict(plan=plan,order=order),indent=2)+'\n')
with (out/'runs.jsonl').open('w') as records:
    for name,seconds in order:
        q=queries[name];stem=name+'.seconds-'+str(seconds)
        profile=out/(stem+'.profile.jsonl');answer=out/(stem+'.rust-original.json');wrapper=out/(stem+'.sh')
        command=[str(ROOT/plan['binary']),'--pnml',str(corpus/q['pnml']),'--xml',str(corpus/q['xml']),'--property-id',q['property_id'],'--method',plan['method'],'--seconds',str(seconds),'--max-states','2000000']
        wrapper.write_text('VASS_PORTFOLIO_PROFILE=1 VASS_RELAXED_PROFILE=1 exec '+shlex.join(command)+' 2>'+shlex.quote(str(profile))+'\n')
        wall,code,expired,resources=run(['/bin/sh',str(wrapper)],ROOT,seconds+2,answer,2048*1024**2,cpus=[8],perf=True)
        validation=run_validation(q,corpus,out,answer,code,args,mode='rust-original-v1',outer_timeout=expired)
        events,other=[],[]
        for line in profile.read_text().splitlines():
            try:events.append(json.loads(line))
            except ValueError:other.append(line)
        row=dict(query=name,seconds=seconds,wall_seconds=wall,exit_code=code,outer_timeout=expired,resources=resources,command=command,events=events,other_profile_lines=other,**validation)
        records.write(json.dumps(row)+'\n');records.flush()
        print(name,seconds,row['verdict'],len(events),flush=True)
for name,expected in plan['required_file_sha256'].items():assert sha(ROOT/name)==expected,name
(out/'completed.json').write_text(json.dumps(dict(rows=len(order),frozen_inputs_unchanged=True))+'\n')
