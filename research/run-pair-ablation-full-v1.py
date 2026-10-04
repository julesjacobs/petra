"""Register and run both pair abstractions on the complete ordinary development cohort."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from process_runner import workspace_workloads

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
corpus=ROOT/'benchmarks/application-portfolio-comparison-v1'
manifest=json.loads((corpus/'manifest.json').read_text());assert len(manifest['queries'])==656
assert sum(q['status']=='imported' for q in manifest['queries'])==640
binary=ROOT/'results/solver-pair-ablation-v1/vass-reach'
runner=ROOT/'results/runner-phase-pair-v1/source'
output=ROOT/'results/local-pair-ablation-full-v1'
assert not output.exists() and not workspace_workloads(ROOT)
command=[sys.executable,str(runner/'scripts/benchmark_smpt_classic.py'),'--corpus',str(corpus),'--binary',str(binary),'--native-tool','native-phase-pair','phase-pair',str(binary),'--native-tool','native-pair','pair',str(binary),'--methods','native-phase-pair','native-pair','--rust-original','--bounded-validation','--validation-seconds','60','--validation-memory-mib','2048','--validation-response-mib','64','--validation-dag-work','200000000','--track-resources','--memory-mib','2048','--max-states','2000000','--outer-grace','0','--seconds','5','--repeat','1','--order-seed','2026092812','--output',str(output)]
paths=[Path(__file__),corpus/'manifest.json',ROOT/'research/pair-ablation-v1-design.md']
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
plan=dict(format='pair-ablation-full-v1',command=command,rows=1312,queries=[q['name'] for q in manifest['queries']],source_slots=656,imported_slots=640,unavailable_slots=16,exact_ordered_branch_representatives=629,file_sha256=pins,binary_sha256=sha(binary),scope='Full656-slot ordinary development cohort,640imports and16unavailable, phase-pair versus same-binary uniform pair. Original PNML/XML including parsing,5s solver, sampled2GiB, independent60s/2GiB check, one local repeat. Every slot retained. No Linux timing comparison or integrated portfolio claim. Both abstractions are incomplete and negative-only. Shared/Linux scripts unchanged;22reserved families untouched.')
with (ROOT/'research/pair-ablation-full-v1-plan.json').open('x') as f:json.dump(plan,f,indent=2);f.write('\n')
env=dict(os.environ)
for k in ['VASS_PORTFOLIO_PROFILE','VASS_RELAXED_PROFILE','VASS_RAW_PHASE_DIAGNOSTICS','VASS_RAW_NEGATIVE_DIAGNOSTICS']:env.pop(k,None)
result=subprocess.run(command,cwd=ROOT,env=env)
with (ROOT/'research/pair-ablation-full-v1-terminal.json').open('x') as f:json.dump(dict(exit_code=result.returncode),f)
sys.exit(result.returncode)
