"""Check both policies on the diagnosed RefineWMG branch, outside cohort timing."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from process_runner import run,workspace_workloads
F=ROOT/'research/count-budget-policy-v1';B=ROOT/'target/release/examples/count_plan_search'
p=ROOT/'benchmarks/general-development-v3/RefineWMG-PT-100101__RC11/branch-4.json'
assert not workspace_workloads(ROOT)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=[]
for policy,expected in [('fixed','unknown'),('state-budget','reachable')]:
 log=F/(policy+'.json');assert not log.exists()
 cmd=[str(B),str(p),'5',policy];wall,code,expired,resources=run(cmd,ROOT,5.3,log,2**31)
 answer=json.loads(log.read_text());assert code==0 and not expired and not resources['memory_limit_exceeded'] and answer['verdict']==expected
 row=dict(policy=policy,command=cmd,wall=wall,exit_code=code,expired=expired,resources=resources,verdict=expected,trace_length=len(answer['trace']),log_sha256=sha(log))
 if expected=='reachable':
  check=F/(policy+'.check.json');cmd=[sys.executable,str(ROOT/'scripts/check_backend_answer.py'),str(p),str(log)]
  w,c,e,r=run(cmd,ROOT,30,check,2**31);assert c==0 and not e and not r['memory_limit_exceeded']
  row['check']=dict(command=cmd,exit_code=c,expired=e,resources=r,log_sha256=sha(check))
 rows.append(row)
record=dict(status='passed',rows=rows,pins={str(q.relative_to(ROOT)):sha(q) for q in [B,p,ROOT/'src/count_plan.rs',ROOT/'examples/count_plan_search.rs',Path(__file__)]},scope=__doc__)
(F/'semantic.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(dict(status='passed',cases=2)))
