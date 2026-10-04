"""Registered two-row frozen-binary n5 regression diagnostic; local only."""
import hashlib, importlib.util, json, os, shutil, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from process_runner import workspace_workloads

def read(p):return json.loads(p.read_text())
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,x):
    with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def module(p,name):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

assert not workspace_workloads(ROOT)
case='write_skew_n5_pairlocked'
corpus='benchmarks/raw-diverse-automaton-v1'
parent=read(ROOT/'research/raw-compressed-cohorts-v1-plan.json')
source=next(s for s in parent['runs'][0]['sources'] if s['name']==case)
assert sha(ROOT/source['query'])==source['query_sha256']
names={n for n in parent['file_sha256'] if n.startswith('scripts/')}
names.update(['scripts/analyze_raw_phase_diagnostics.py','research/run-raw-n5-control-diagnostic-v1.py',corpus+'/collection.json',corpus+'/source-manifest.json',source['query']])
runs=[]
for config,folder in [('dense','solver-raw-balanced-v1'),('compressed','solver-walk-sparse-v1')]:
    binary=ROOT/'results'/folder/'vass-reach';prov=read(binary.with_name('provenance.json'))
    assert sha(binary)==prov['binary_sha256'] and sha(binary.with_name('source.tar.gz'))==prov['source_sha256']
    output='results/raw-n5-control-diagnostic-v1-'+config
    assert not (ROOT/output).exists()
    command=[sys.executable,'scripts/benchmark_stress_raw.py','--corpus',corpus,'--output',output,'--binary',str(binary),'--methods','raw-portfolio-balanced','--case',case,'--seconds','60','--memory-mib','2048','--repeat','1','--solver-fraction','0.8','--max-states','100000000']
    runs.append(dict(configuration=config,output=output,command=command,binary_sha256=prov['binary_sha256'],source_archive_sha256=prov['source_sha256']))
    names.add(str(binary.with_name('provenance.json').relative_to(ROOT)))
pins={n:sha(ROOT/n) for n in sorted(names)}
for n in names:
    if n.startswith('scripts/') and n in parent['file_sha256']:assert pins[n]==parent['file_sha256'][n]
plan=dict(format='raw-n5-control-diagnostic-v1',runs=runs,rows=2,query=source,limits=dict(seconds=60,memory_mib=2048,max_states=100000000,solver_fraction=0.8,repeat=1),environment={'VASS_RAW_PHASE_DIAGNOSTICS':'1'},file_sha256=pins,scope='One original n5 query, existing dense versus compressed frozen binaries, same balanced scheduler and checker. Charge2d->8d is a known confound. Phase attribution only; no competitive timing claim. Local only; preserve censored/truncated spans and independent checks.')
plan_path=ROOT/'research/raw-n5-control-diagnostic-v1-plan.json';save(plan_path,plan)
env=dict(os.environ,VASS_RAW_PHASE_DIAGNOSTICS='1');env.pop('VASS_RAW_NEGATIVE_DIAGNOSTICS',None)
combined=[];artifacts={str(plan_path.relative_to(ROOT)):sha(plan_path)}
for run in runs:
    assert not workspace_workloads(ROOT)
    assert all(sha(ROOT/n)==h for n,h in pins.items())
    print('Starting '+run['configuration'],flush=True)
    subprocess.run(run['command'],cwd=ROOT,env=env,check=True)
    out=ROOT/run['output'];recorded=read(out/'environment.json')
    assert sha(out/'vass-reach')==recorded['binary_sha256']==run['binary_sha256']
    for n,h in recorded['runner_sha256'].items():assert sha(out/'runner-source'/n)==h==pins['scripts/'+n]
    frozen_analyzer=out/'runner-source/analyze_raw_phase_diagnostics.py';shutil.copyfile(ROOT/'scripts/analyze_raw_phase_diagnostics.py',frozen_analyzer)
    assert sha(frozen_analyzer)==pins['scripts/analyze_raw_phase_diagnostics.py']
    classifier=module(out/'runner-source/benchmark_stress_raw.py','frozen_classifier')
    analyzer=module(frozen_analyzer,'frozen_analyzer')
    rows=[json.loads(l) for l in (out/'runs.jsonl').read_text().splitlines()];assert len(rows)==1
    row=rows[0];assert (row['query'],row['method'],row['repeat'])==(case,'raw-portfolio-balanced',0)
    assert row['query_sha256']==source['query_sha256']==sha(out/'inputs'/(case+'.json'))
    d=out/(case+'.raw-portfolio-balanced.0')
    classified,expired,usage=classifier.classify_bounded_worker(d,row['worker_exit_code'],row['outer_timeout'],row['usage'],row['wall_seconds'],60,2048*1024**2)
    assert all(row.get(k)==v for k,v in classified.items()) and expired==row['outer_timeout'] and usage==row['usage']
    if row['verdict'] in ('reachable','unreachable'):
        assert row['independent_check'] and not expired and not usage['memory_limit_exceeded']
        assert row['worker_exit_code']==row['solver_exit_code']==0
        assert read(d/'solver.stdout')['verdict']==row['verdict']
    with (d/'solver.stderr').open(errors='replace') as f:phases=analyzer.analyze(f)
    phases['source_sha256']=sha(d/'solver.stderr');assert not phases['issues']
    save(d/'phase-analysis.json',phases)
    combined.append(dict(configuration=run['configuration'],row=row,phases=phases))
    for p in [out/'runs.jsonl',out/'environment.json',out/'sources.json',frozen_analyzer,*d.glob('*')]:
        if p.is_file():artifacts[str(p.relative_to(ROOT))]=sha(p)
save(ROOT/'research/raw-n5-control-diagnostic-v1-analysis.json',combined)
assert len({item['row']['verdict'] for item in combined}&{'reachable','unreachable'})<=1
verification=dict(status='passed',rows=2,statuses={i['configuration']:i['row']['status'] for i in combined},artifact_sha256=artifacts,scope='Frozen-artifact and classifier reconciliation of saved independent-check responses. No proof reruns; phase censoring retained.')
save(ROOT/'research/raw-n5-control-diagnostic-v1-verification.json',verification)
print(json.dumps({k:v for k,v in verification.items() if k!='artifact_sha256'},indent=2),flush=True)
