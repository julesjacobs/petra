"""Bounded structural diagnostics, without original-net reachability claims."""
import hashlib,json,sys,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from process_runner import run,workspace_workloads
F=ROOT/'research/cloud-reduction-diagnostics-v1';B=ROOT/'target/release/examples/reduction_diagnostic'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not workspace_workloads(ROOT) and not (F/'plan.json').exists()
inputs=sorted((ROOT/'benchmarks/general-development-v3/CloudReconfiguration-PT-311__RC06').glob('branch-*.json'))
paths=[B,Path(__file__),ROOT/'examples/reduction_diagnostic.rs',ROOT/'src/buffer_agglomeration.rs',ROOT/'src/relevance.rs',ROOT/'src/model.rs',ROOT/'scripts/process_runner.py']
for p in paths:
 dest=F/'snapshot'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
plan=dict(scope=__doc__,pins={str(p.relative_to(ROOT)):sha(p) for p in paths},inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},outer_seconds=5.3,memory_bytes=2**31)
(F/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');rows=[]
for p in inputs:
 log=F/(p.stem+'.log');out=F/(p.stem+'.reduced.json');cmd=[str(F/'snapshot'/B.relative_to(ROOT)),str(p),str(out)]
 wall,code,expired,resources=run(cmd,ROOT,5.3,log,2**31)
 row=dict(input=str(p.relative_to(ROOT)),command=cmd,wall=wall,exit_code=code,expired=expired,resources=resources,log_sha256=sha(log))
 rows.append(row);print(p.stem,code,log.read_text()[:1800],flush=True)
(F/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
