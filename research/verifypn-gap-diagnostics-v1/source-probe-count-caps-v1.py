"""Targeted cap ablation for an independently proved count-cap gap; no cohort claim."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from process_runner import run,workspace_workloads
F=ROOT/'research/verifypn-gap-diagnostics-v1';B=ROOT/'target/release/examples/count_plan_diagnostic'
p=ROOT/'benchmarks/general-development-v3/RefineWMG-PT-100101__RC11/branch-4.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not workspace_workloads(ROOT);assert not (F/'cap-plan.json').exists()
plan=dict(scope=__doc__,caps=[8192,16384,65536],seconds=5,outer_seconds=5.3,checker_seconds=30,memory_bytes=2**31,pins={str(f.relative_to(ROOT)):sha(f) for f in [p,B,ROOT/'src/count_plan.rs',ROOT/'examples/count_plan_diagnostic.rs',Path(__file__),ROOT/'scripts/check_backend_answer.py',ROOT/'scripts/process_runner.py']})
(F/'cap-plan.json').write_text(json.dumps(plan,indent=2)+'\n');rows=[]
for cap in plan['caps']:
 log=F/f'cap-{cap}.json';cmd=[str(B),str(p),str(cap),'5']
 wall,code,expired,resources=run(cmd,ROOT,5.3,log,2**31)
 try:answer=json.loads(log.read_text())
 except ValueError:answer={}
 row=dict(cap=cap,command=cmd,wall=wall,exit_code=code,expired=expired,resources=resources,log_sha256=sha(log),verdict=answer.get('verdict'),reason=answer.get('reason'),trace_length=len(answer.get('trace',[])))
 if row['verdict']=='reachable' and not expired and code==0:
  check=F/f'cap-{cap}.check.json';checkcmd=[sys.executable,str(ROOT/'scripts/check_backend_answer.py'),str(p),str(log)]
  cw,cc,ce,cr=run(checkcmd,ROOT,30,check,2**31);assert cc==0 and not ce and not cr['memory_limit_exceeded']
  row['check']=dict(command=checkcmd,log_sha256=sha(check),exit_code=cc,expired=ce,resources=cr)
 rows.append(row);print(json.dumps(row),flush=True)
 (F/'cap-results.json').write_text(json.dumps(rows,indent=2)+'\n')
