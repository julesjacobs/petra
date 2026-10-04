"""Audit the complete reduction-round ablation and saved check receipts."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'research/cloud-reduction-rounds-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((F/'plan.json').read_text());rows=json.loads((F/'results.json').read_text())
assert json.loads((F/'terminal.json').read_text())==dict(exit_code=0,rows=6)
for name,d in p['pins'].items():assert sha(F/'snapshot'/name)==d,name
for name,d in p['inputs'].items():assert sha(ROOT/name)==d,name
assert [(r['branch'],r['rounds']) for r in rows]==[(i,n) for i in [0,1] for n in [0,1,2]]
for r in rows:
 stem=f"branch-{r['branch']}.rounds-{r['rounds']}"
 assert sha(F/(stem+'.json'))==r['log_sha256']
 assert r['exit_code']==0 and not r['expired'] and not r['resources']['memory_limit_exceeded']
 if r['rounds']==2:
  assert r['verdict']=='unreachable'
  c=r['check'];assert c['exit_code']==0 and not c['expired'] and not c['resources']['memory_limit_exceeded']
  assert sha(F/(stem+'.check.json'))==c['log_sha256']
  assert json.loads((F/(stem+'.check.json')).read_text())['status']=='passed'
 else:assert r['verdict']=='unknown' and r['states']==200000 and r['reason']=='state limit'
result=dict(status='passed',rows=6,plan_sha256=sha(F/'plan.json'),results_sha256=sha(F/'results.json'),conclusion='At identical200k-state/3s limits, zero and one reduction round exhaust the state budget; two rounds prove both branches unreachable. Larger state budgets and stable timing unmeasured.')
(F/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
