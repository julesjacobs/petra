"""Original PNML/XML diagnostic with independently translated and checked answers."""
import hashlib,json,sys
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from process_runner import run,workspace_workloads
from bounded_validation import run_validation
F=ROOT/'research/count-budget-policy-v1';C=ROOT/'benchmarks/general-development-v3';B=ROOT/'target/release/vass-reach'
q=next(q for q in json.loads((C/'manifest.json').read_text())['queries'] if q['name']=='RefineWMG-PT-100101__RC11')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not workspace_workloads(ROOT);assert not (F/'original-plan.json').exists()
plan=dict(scope=__doc__,query=q,seconds=5,outer_seconds=5.3,memory_bytes=2**31,methods=['sparse-count-plan','sparse-count-plan-budget'],pins={str(p.relative_to(ROOT)):sha(p) for p in [B,ROOT/'src/count_plan.rs',ROOT/'src/main.rs',Path(__file__)]})
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
