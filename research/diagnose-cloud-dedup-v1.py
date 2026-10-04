"""Exact duplicate-transition ablation on diagnostic reduced nets, not original verdicts."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from process_runner import run,workspace_workloads
F=ROOT/'research/cloud-reduction-diagnostics-v1';O=F/'dedup';O.mkdir()
B=F/'snapshot/target/release/examples/reduction_diagnostic'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not workspace_workloads(ROOT)
plan=dict(scope=__doc__,script_sha256=sha(Path(__file__)),binary_sha256=sha(B),inputs={str(p.relative_to(ROOT)):sha(p) for p in sorted(F.glob('*.reduced.json'))})
(O/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');rows=[]
for name in plan['inputs']:
 p=ROOT/name;problem=json.loads(p.read_text());seen=set();transitions=[];mapping=[]
 for i,t in enumerate(problem['transitions']):
  key=(tuple(sorted(map(tuple,t['pre']))),tuple(sorted(map(tuple,t['post']))))
  if key not in seen:seen.add(key);transitions.append(t);mapping.append(i)
 problem['transitions']=transitions
 inp=O/p.name;inp.write_text(json.dumps(problem)+'\n');(O/(p.stem+'.mapping.json')).write_text(json.dumps(mapping)+'\n')
 out=O/(p.stem+'.normalized.json');log=O/(p.stem+'.log');cmd=[str(B),str(inp),str(out)]
 wall,code,expired,resources=run(cmd,ROOT,5.3,log,2**31)
 rows.append(dict(command=cmd,wall=wall,exit_code=code,expired=expired,resources=resources,log_sha256=sha(log),input_sha256=sha(inp),output_sha256=sha(out) if out.exists() else None))
 print(p.name,len(transitions),log.read_text()[:2000],flush=True)
(O/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
