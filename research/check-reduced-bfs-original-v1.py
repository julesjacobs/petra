"""Original PNML/XML diagnostic with independently translated and checked answers."""
import hashlib,json,sys,shutil
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from process_runner import run,workspace_workloads
from bounded_validation import run_validation
F=ROOT/'research/reduced-bfs-v1';C=ROOT/'benchmarks/general-development-v3';SNAP=F/'snapshot';B=SNAP/'vass-reach'
q=next(q for q in json.loads((C/'manifest.json').read_text())['queries'] if q['name']=='CloudReconfiguration-PT-311__RC06')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not workspace_workloads(ROOT);assert not (F/'original-plan.json').exists()
SNAP.mkdir()
paths=list((ROOT/'src').glob('*.rs'))+list((ROOT/'scripts').glob('*.py'))+[ROOT/'Cargo.toml',ROOT/'Cargo.lock',ROOT/'tests/reduced_bfs.rs',Path(__file__)]
paths += [p for p in (ROOT/'vendor/varisat').rglob('*') if p.is_file() and '.git' not in p.parts and 'target' not in p.parts]
for p in paths:
 dest=SNAP/'source'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
shutil.copy2(ROOT/'target/release/vass-reach',B)
plan=dict(source_sha256={str(p.relative_to(ROOT)):sha(p) for p in paths},input_sha256={str(C/q[k]):sha(C/q[k]) for k in ['pnml','xml']},scope=__doc__,query=q,seconds=5,outer_seconds=5.3,memory_bytes=2**31,methods=['portfolio-walk-counts','reduced-bfs'],pins={str(p.relative_to(ROOT)):sha(p) for p in [B,ROOT/'src/count_plan.rs',ROOT/'src/main.rs',Path(__file__)]})
(F/'original-plan.json').write_text(json.dumps(plan,indent=2)+'\n');rows=[]
args=SimpleNamespace(native_python=sys.executable,validation_memory_mib=2048,validation_response_mib=64,validation_seconds=30,validation_dag_work=200000000)
for mode in plan['methods']:
 log=F/(mode+'.original.json')
 cmd=[str(B),'--pnml',str(C/q['pnml']),'--xml',str(C/q['xml']),'--property-id',q['property_id'],'--method',mode,'--seconds','5','--max-states','2000000','--buffer-agglomeration']
 wall,code,expired,resources=run(cmd,ROOT,5.3,log,2**31)
 validation=run_validation(q,C,F,log,code,args,mode='rust-original-v1',outer_timeout=expired)
 row=dict(method=mode,command=cmd,wall=wall,exit_code=code,expired=expired,resources=resources,log_sha256=sha(log),validation=validation)
 assert validation['verdict']!='error',validation
 rows.append(row);print(mode,validation['verdict'],validation.get('independent_checks'),flush=True)
(F/'original-results.json').write_text(json.dumps(rows,indent=2)+'\n')
