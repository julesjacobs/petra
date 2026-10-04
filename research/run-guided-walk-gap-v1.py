"""Register all eight current native-walk gaps for a three-way guided-walk pilot."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from process_runner import workspace_workloads

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
parent=ROOT/'benchmarks/application-portfolio-comparison-v1'
audit_path=ROOT/'research/application-walk-full-v1/audit.json'
audit=json.loads(audit_path.read_text());assert audit['status']=='passed'
rows_path=ROOT/'results/linux-application-walk-full-v1/runs.jsonl'
assert sha(rows_path)==audit['artifact_sha256'][str(rows_path.relative_to(ROOT))]
rows=[json.loads(line) for line in rows_path.read_text().splitlines()]
assert len(rows)==3280
selected={r['query'] for r in rows if r['method']=='native-walk' and r['collection_status']=='imported' and r['verdict']=='unknown'}
assert len(selected)==8
assert not workspace_workloads(ROOT)
corpus=ROOT/'research/guided-walk-gap-v1/corpus';corpus.mkdir(parents=True)
manifest=json.loads((parent/'manifest.json').read_text())
manifest['queries']=[q for q in manifest['queries'] if q['name'] in selected]
for q in manifest['queries']:
    for field in ['net','property','pnml','xml']:
        if field in q:q[field]=os.path.relpath((parent/q[field]).resolve(),corpus)
    for branch in q['branches']:branch['path']=os.path.relpath((parent/branch['path']).resolve(),corpus)
manifest['scope']='All eight native-walk Unknowns from the complete audited3280-row development comparison; selected diagnostic cohort, not held out.'
(corpus/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
binary=ROOT/'results/solver-guided-walk-v1/vass-reach'
runner=ROOT/'results/runner-phase-pair-v1/source'
output=ROOT/'results/local-guided-walk-gap-v1'
assert not output.exists()
command=[sys.executable,str(runner/'scripts/benchmark_smpt_classic.py'),'--corpus',str(corpus),'--binary',str(binary)]
for label,engine in [('native-uniform','walk'),('native-incremental','walk-incremental'),('native-guided','walk-guided')]:
    command+=['--native-tool',label,engine,str(binary)]
command+=['--methods','native-uniform','native-incremental','native-guided','--rust-original','--bounded-validation','--validation-seconds','60','--validation-memory-mib','2048','--validation-response-mib','64','--validation-dag-work','200000000','--track-resources','--memory-mib','2048','--max-states','2000000','--outer-grace','0','--seconds','5','--repeat','1','--order-seed','2026092813','--output',str(output)]
paths=[Path(__file__),corpus/'manifest.json',ROOT/'research/guided-walk-v1-design.md',audit_path,rows_path,parent/'manifest.json']
for parent, names in [(binary.parent,['vass-reach','provenance.json','source.tar.gz','source-files-sha256.json']),(runner.parent,['provenance.json','runner.tar.gz','files-sha256.json'])]:paths.extend(parent/name for name in names)
closure=json.loads((runner.parent/'files-sha256.json').read_text())
for name,digest in closure.items():assert sha(runner/name)==digest;paths.append(runner/name)
for q in manifest['queries']:
    if q['status']!='imported':
        continue
    for field in ['net','property','pnml','xml']:
        if field in q:
            p=corpus/q[field];assert sha(p)==q[field+'_sha256'];paths.append(p.resolve())
    for b in q['branches']:
        p=corpus/b['path'];assert sha(p)==b['sha256'];paths.append(p.resolve())
pins={str(p.relative_to(ROOT)):sha(p) for p in paths}
plan=dict(format='guided-walk-gap-v1',command=command,rows=24,queries=[q['name'] for q in manifest['queries']],source_slots=8,parent_slots=656,parent_imports=640,parent_unavailable=16,file_sha256=pins,binary_sha256=sha(binary),scope='All8native-walk Unknowns from the audited656-slot parent, three same-binary walk modes: uniform, incremental-target uniform, guided. Original PNML/XML,5s solver, sampled2GiB, separate60s validation, one local repeat, seed0. Selected diagnostic only. No broad superiority, integrated portfolio, or cross-machine speed claim.22reserved families untouched.')
with (ROOT/'research/guided-walk-gap-v1-plan.json').open('x') as f:json.dump(plan,f,indent=2);f.write('\n')
env=dict(os.environ)
for k in ['VASS_PORTFOLIO_PROFILE','VASS_RELAXED_PROFILE','VASS_RAW_PHASE_DIAGNOSTICS','VASS_RAW_NEGATIVE_DIAGNOSTICS']:env.pop(k,None)
result=subprocess.run(command,cwd=ROOT,env=env)
with (ROOT/'research/guided-walk-gap-v1-terminal.json').open('x') as f:json.dump(dict(exit_code=result.returncode),f)
sys.exit(result.returncode)
