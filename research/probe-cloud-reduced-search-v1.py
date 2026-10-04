"""Search diagnostic reduced nets; checked answers apply only to these reduced inputs."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from process_runner import run,workspace_workloads
F=ROOT/'research/cloud-reduction-diagnostics-v1';O=F/'search';O.mkdir()
B=ROOT/'results/solver-portfolio-counts-development-v1/candidate';S=ROOT/'results/solver-portfolio-counts-development-v1/source/scripts/check_backend_answer.py'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not workspace_workloads(ROOT)
inputs=sorted(F.glob('*.reduced.json'))+sorted((F/'dedup').glob('*.normalized.json'))
plan=dict(scope=__doc__,seconds=3,outer_seconds=3.3,memory_bytes=2**31,max_states=2000000,binary=str(B),binary_sha256=sha(B),checker_sha256=sha(S),script_sha256=sha(Path(__file__)),inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},methods=['bfs','portfolio-walk-counts'])
(O/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');rows=[]
for p in inputs:
 for method in plan['methods']:
  label=p.stem+'.'+method;log=O/(label+'.json');cmd=[str(B),'--json',str(p),'--method',method,'--seconds','3','--max-states','2000000']
  wall,code,expired,resources=run(cmd,ROOT,3.3,log,2**31)
  try:a=json.loads(log.read_text())
  except ValueError:a={}
  row=dict(input=str(p.relative_to(ROOT)),method=method,command=cmd,wall=wall,exit_code=code,expired=expired,resources=resources,log_sha256=sha(log),verdict=a.get('verdict','unknown'),reason=a.get('reason'),states=a.get('states'))
  if row['verdict']!='unknown' and code==0 and not expired:
   check=O/(label+'.check.json');cw,cc,ce,cr=run([sys.executable,str(S),str(p),str(log)],ROOT,30,check,2**31)
   row['check']=dict(exit_code=cc,expired=ce,resources=cr,wall=cw,log_sha256=sha(check));assert cc==0 and not ce and not cr['memory_limit_exceeded']
  rows.append(row);(O/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
  print(label,row['verdict'],row['reason'],row['states'],flush=True)
(O/'terminal.json').write_text(json.dumps(dict(exit_code=0,rows=len(rows)))+'\n')
