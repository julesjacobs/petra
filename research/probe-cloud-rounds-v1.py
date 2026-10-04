"""Complete two-branch reduction-round ablation with fixed BFS limits."""
import hashlib,json,sys,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from process_runner import run,workspace_workloads
F=ROOT/'research/cloud-reduction-rounds-v1';B=ROOT/'target/release/examples/reduced_closure_diagnostic';CHECK=ROOT/'research/check-cloud-reduced-closure-v1.py'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not workspace_workloads(ROOT) and not (F/'plan.json').exists()
paths=[B,CHECK,Path(__file__),ROOT/'examples/reduced_closure_diagnostic.rs']+list((ROOT/'src').glob('*.rs'))+list((ROOT/'scripts').glob('*.py'))
for p in paths:
 dest=F/'snapshot'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
inputs=sorted((ROOT/'benchmarks/general-development-v3/CloudReconfiguration-PT-311__RC06').glob('branch-*.json'))
plan=dict(scope=__doc__,rounds=[0,1,2],seconds=3,outer_seconds=3.3,max_states=200000,memory_bytes=2**31,checker_seconds=30,pins={str(p.relative_to(ROOT)):sha(p) for p in paths},inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs})
(F/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');rows=[]
for i,p in enumerate(inputs):
 for rounds in plan['rounds']:
  log=F/f'branch-{i}.rounds-{rounds}.json';cmd=[str(F/'snapshot'/B.relative_to(ROOT)),str(p),str(rounds)]
  wall,code,expired,resources=run(cmd,ROOT,3.3,log,2**31)
  a=json.loads(log.read_text()) if code==0 and not expired else {}
  row=dict(branch=i,rounds=rounds,command=cmd,wall=wall,exit_code=code,expired=expired,resources=resources,log_sha256=sha(log),verdict=a.get('answer',{}).get('verdict','unknown'),states=a.get('answer',{}).get('states'),reason=a.get('answer',{}).get('reason'))
  if row['verdict']=='unreachable':
   check=F/f'branch-{i}.rounds-{rounds}.check.json';cw,cc,ce,cr=run([sys.executable,str(CHECK),str(i),str(log)],ROOT,30,check,2**31)
   row['check']=dict(exit_code=cc,expired=ce,resources=cr,wall=cw,log_sha256=sha(check));assert cc==0 and not ce and not cr['memory_limit_exceeded']
  rows.append(row);(F/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
  print(i,rounds,row['verdict'],row['states'],row['reason'],flush=True)
(F/'terminal.json').write_text(json.dumps(dict(exit_code=0,rows=len(rows)))+'\n')
