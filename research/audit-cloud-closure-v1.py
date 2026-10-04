"""Audit preserved diagnostic reduction chains and independent original-input checks."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'research/cloud-reduction-diagnostics-v1/closure'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((F/'plan.json').read_text());rows=json.loads((F/'results.json').read_text())
assert json.loads((F/'terminal.json').read_text())==dict(exit_code=0,rows=2)
for name,digest in p['pins'].items():assert sha(F/'snapshot'/name)==digest,name
for name,digest in p['inputs'].items():assert sha(ROOT/name)==digest,name
assert [r['branch'] for r in rows]==[0,1]
summary=[]
for r in rows:
 i=r['branch'];log=F/f'branch-{i}.json';checklog=F/f'branch-{i}.check.json'
 assert sha(log)==r['log_sha256'] and sha(checklog)==r['check']['log_sha256']
 assert r['exit_code']==0 and not r['expired'] and not r['resources']['memory_limit_exceeded']
 c=r['check'];assert c['exit_code']==0 and not c['expired'] and not c['resources']['memory_limit_exceeded']
 receipt=json.loads(checklog.read_text());assert receipt['status']=='passed' and receipt['branch']==i
 assert receipt['check']=='original-input-reduction-chain-and-finite-closure'
 a=json.loads(log.read_text());assert a['answer']['verdict']=='unreachable'
 summary.append(dict(branch=i,states=a['answer']['states'],reductions=len(a['reductions']),places=receipt['places'],transitions=receipt['transitions'],diagnostic_wall_seconds=r['wall'],checker_wall_seconds=c['wall']))
result=dict(status='passed',original_property_verdict='unreachable',branches=summary,plan_sha256=sha(F/'plan.json'),results_sha256=sha(F/'results.json'),scope='Independent original translation, reconstructed sound reductions and exhaustive closure checks for both branches. Diagnostic per-branch budgets, not matched production-portfolio performance.')
(F/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
