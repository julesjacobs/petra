"""Check fetched preflight evidence before dispatching the full cohort."""
import hashlib,json,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'research/portfolio-reduced-linux-v1';O=ROOT/'results/linux-portfolio-reduced-capability-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((F/'plan.json').read_text());r=json.loads((F/'capability.json').read_text())
assert r['status']=='passed' and r['plan_sha256']==sha(F/'plan.json')
assert r['methods']==list(p['methods']) and r['runner_archive_sha256']==p['runner_archive_sha256']
assert r['runs_sha256']==sha(O/'runs.jsonl') and r['environment_sha256']==sha(O/'environment.json')
assert r['harness_receipt_sha256']==sha(F/'capability-harness.json')
rows=[json.loads(x) for x in (O/'runs.jsonl').read_text().splitlines()]
assert Counter((x['query'],x['method']) for x in rows)==Counter((q,m) for q in r['expected'] for m in p['methods'])
for x in rows:
 assert x['property_truth'] is r['expected'][x['query']]
 assert x['exit_code']==0 and not x['outer_timeout']
 assert x['resources']['cpus']==[8] and x['resources']['memory_limit_bytes']==2**31
 if x['method'].startswith('native-'):assert x['independent_checks'] and x['validation']['exit_code']==0
for x in r['component_rows']:
 assert x['passed'] and x['exit_code']==0 and not x['expired']
 assert sha(F/'components'/f"{x['method']}-{x['label']}.log")==x['log_sha256']
sys.path.insert(0,str(ROOT/'scripts'))
from analyze_application_expansion import registered_native_tools
registered_native_tools(p,json.loads((O/'environment.json').read_text()))
closure=json.loads((F/'closure/receipt.json').read_text())
assert closure['status']=='passed' and closure['parent_plan_sha256']==sha(F/'plan.json')
assert closure['plan_sha256']==sha(F/'closure/plan.json')
cp=json.loads((F/'closure/plan.json').read_text())
assert cp['script_sha256']==sha(ROOT/'research/preflight-portfolio-reduced-closure-v1.py')
assert cp['binary_sha256']==p['native_tools']['native-reduced']['binary_sha256']
assert closure['row']['log_sha256']==sha(F/'closure/answer.json')
assert closure['proof_leaves']==['finite-closure-v1']*2
v=closure['validation'];assert v['verdict']=='unreachable' and len(v['independent_checks'])==2
assert v['validation']['exit_code']==0 and not v['validation']['outer_timeout']
result=dict(closure_receipt_sha256=sha(F/'closure/receipt.json'),status='passed' ,harness_rows=len(rows),component_rows=len(r['component_rows']),plan_sha256=sha(F/'plan.json'),capability_sha256=sha(F/'capability.json'))
with (F/'capability-audit.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
