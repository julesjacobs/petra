"""Exercise the new nested closure format on original Cloud input with Linux limits."""
import hashlib,json,sys
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'research/portfolio-reduced-linux-v1';O=F/'closure';O.mkdir()
plan=json.loads((F/'plan.json').read_text());sys.path.insert(0,str(ROOT/plan['runner_source']/'scripts'))
from process_runner import workspace_workloads
from linux_runner import run
from bounded_validation import run_validation
assert sys.platform=='linux' and not workspace_workloads(ROOT)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
C=ROOT/plan['corpus'];q=next(q for q in json.loads((C/'manifest.json').read_text())['queries'] if q['name']=='CloudReconfiguration-PT-311__RC06')
B=Path(plan['native_tools']['native-reduced']['binary']);assert sha(B)==plan['native_tools']['native-reduced']['binary_sha256']
cmd=[str(B),'--pnml',str(C/q['pnml']),'--xml',str(C/q['xml']),'--property-id',q['property_id'],'--method','portfolio-reduced','--seconds','5','--max-states','2000000','--buffer-agglomeration']
(O/'plan.json').write_text(json.dumps(dict(scope=__doc__,parent_plan_sha256=sha(F/'plan.json'),script_sha256=sha(Path(__file__)),query=q,command=cmd,binary_sha256=sha(B),cpus=[8],memory_bytes=2**31,seconds=5),indent=2)+'\n')
log=O/'answer.json';wall,code,expired,res=run(cmd,ROOT,5,log,2**31,cpus=[8],perf=True)
row=dict(wall=wall,exit_code=code,expired=expired,resources=res,log_sha256=sha(log))
(O/'execution.json').write_text(json.dumps(row,indent=2)+'\n')
assert code==0 and not expired and not res.get('memory_limit_exceeded'),row
args=SimpleNamespace(native_python=str(ROOT/'vendor/venv/bin/python'),validation_memory_mib=2048,validation_response_mib=64,validation_seconds=60,validation_dag_work=200000000)
v=run_validation(q,C,O,log,code,args,mode='rust-original-v1')
a=json.loads(log.read_text());leaves=[]
for attempt in a['attempts']:
 leaf=attempt['outcome']['proof']
 while 'inner' in leaf:leaf=leaf['inner']
 leaves.append(leaf['kind'])
assert leaves==['finite-closure-v1']*2,leaves
assert v['verdict']=='unreachable' and len(v['independent_checks'])==2,v
r=dict(status='passed',parent_plan_sha256=sha(F/'plan.json'),plan_sha256=sha(O/'plan.json'),row=row,validation=v,proof_leaves=leaves,scope='Qualification only; this extra invocation is excluded from the full comparison.')
(O/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(status=r['status'],proof_leaves=leaves,checks=v['independent_checks'])))
