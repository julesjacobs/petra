"""Preserve and independently verify diagnostic original-input closure proofs."""
import hashlib,json,sys,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from process_runner import run,workspace_workloads
F=ROOT/'research/cloud-reduction-diagnostics-v1/closure';F.mkdir()
B=ROOT/'target/release/examples/reduced_closure_diagnostic';S=ROOT/'research/check-cloud-reduced-closure-v1.py'
C=ROOT/'benchmarks/general-development-v3';q=next(q for q in json.loads((C/'manifest.json').read_text())['queries'] if q['name']=='CloudReconfiguration-PT-311__RC06')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not workspace_workloads(ROOT)
paths=[B,S,Path(__file__),ROOT/'examples/reduced_closure_diagnostic.rs',ROOT/'Cargo.toml',ROOT/'Cargo.lock']+list((ROOT/'src').glob('*.rs'))+list((ROOT/'scripts').glob('*.py'))
for p in paths:
 dest=F/'snapshot'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
plan=dict(scope=__doc__,query=q,seconds_per_branch=3,outer_seconds=3.3,memory_bytes=2**31,checker_seconds=30,pins={str(p.relative_to(ROOT)):sha(p) for p in paths},inputs={str(p.relative_to(ROOT)):sha(p) for p in [C/q['pnml'],C/q['xml']]+[C/b['path'] for b in q['branches']]})
(F/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');rows=[]
for i,b in enumerate(q['branches']):
 log=F/f'branch-{i}.json';cmd=[str(B),str(C/b['path'])]
 wall,code,expired,resources=run(cmd,ROOT,3.3,log,2**31)
 row=dict(branch=i,command=cmd,wall=wall,exit_code=code,expired=expired,resources=resources,log_sha256=sha(log))
 assert code==0 and not expired and not resources['memory_limit_exceeded']
 check=F/f'branch-{i}.check.json';command=[sys.executable,str(S),str(i),str(log)]
 cw,cc,ce,cr=run(command,ROOT,30,check,2**31)
 row['check']=dict(command=command,wall=cw,exit_code=cc,expired=ce,resources=cr,log_sha256=sha(check))
 rows.append(row);(F/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
 print(i,cc,check.read_text()[:1500],flush=True)
 assert cc==0 and not ce and not cr['memory_limit_exceeded']
(F/'terminal.json').write_text(json.dumps(dict(exit_code=0,rows=len(rows)))+'\n')
