"""Exploratory per-branch diagnostics; not a fair whole-property comparison."""
from pathlib import Path
import hashlib,json,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from process_runner import run,workspace_workloads
F=ROOT/'research/verifypn-gap-diagnostics-v1';B=ROOT/'results/solver-walk-sparse-v1/vass-reach'
assert not workspace_workloads(ROOT)
assert not (F/'plan.json').exists()
queries=['CloudReconfiguration-PT-311__RC06','RefineWMG-PT-100101__RC11']
inputs=[p for q in queries for p in sorted((ROOT/'benchmarks/general-development-v3'/q).glob('branch-*.json'))]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=dict(scope=__doc__,binary=str(B),binary_sha256=sha(B),inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},methods=['portfolio-walk','sparse-count-plan'],seconds_per_branch=2,outer_seconds=2.2,memory_bytes=2**31,checker_seconds=30)
(F/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
rows=[]
for p in inputs:
 for method in plan['methods']:
  label=p.parent.name+'.'+p.stem+'.'+method;log=F/(label+'.json')
  cmd=[str(B),'--json',str(p),'--method',method,'--seconds','2','--max-states','2000000']
  wall,code,expired,resources=run(cmd,ROOT,2.2,log,2**31)
  try:answer=json.loads(log.read_text())
  except ValueError:answer={}
  row=dict(input=str(p.relative_to(ROOT)),method=method,command=cmd,wall=wall,exit_code=code,expired=expired,resources=resources,log_sha256=sha(log),answer=answer)
  if answer.get('verdict') in ['reachable','unreachable'] and code==0 and not expired:
   checker=[sys.executable,str(ROOT/'scripts/check_backend_answer.py'),str(p),str(log)]
   checklog=F/(label+'.check.json')
   cw,cc,ce,cr=run(checker,ROOT,30,checklog,2**31)
   row['check']=dict(exit_code=cc,expired=ce,resources=cr,log_sha256=sha(checklog),command=checker)
   assert cc==0 and not ce and not cr['memory_limit_exceeded'],row
  rows.append(row)
  with (F/'runs.jsonl').open('a') as stream:stream.write(json.dumps(row)+'\n')
  print(label,answer.get('verdict'),answer.get('reason'),flush=True)
(F/'terminal.json').write_text(json.dumps(dict(exit_code=0,rows=len(rows),finished=time.time()))+'\n')
