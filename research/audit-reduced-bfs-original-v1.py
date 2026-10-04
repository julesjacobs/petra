"""Audit saved full original-input reduced-BFS validation and immutable identities."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'research/reduced-bfs-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((F/'original-plan.json').read_text())
for name,d in p['source_sha256'].items():assert sha(F/'snapshot/source'/name)==d,name
for name,d in p['input_sha256'].items():assert sha(Path(name))==d,name
assert sha(F/'snapshot/vass-reach')==p['pins']['research/reduced-bfs-v1/snapshot/vass-reach']
rows=json.loads((F/'original-results.json').read_text());assert [r['method'] for r in rows]==p['methods']
for r in rows:
 log=F/(r['method']+'.original.json');assert sha(log)==r['log_sha256']
 v=r['validation'];c=v['validation'];assert c['exit_code']==0 and not c['outer_timeout'] and not c['resources']['memory_limit_exceeded']
 if r['method']=='reduced-bfs':
  assert r['exit_code']==0 and not r['expired'] and not r['resources']['memory_limit_exceeded'] and r['wall']<p['seconds']
  assert v['verdict']=='unreachable' and not v['deadline_exceeded']
  assert v['translation_check']=='independent-original-input-equals-all-canonical-branches'
  assert len(v['branches'])==2 and all(b['verdict']=='unreachable' and b['independent_check']=='python-buffer-agglomeration' for b in v['branches'])
  a=json.loads(log.read_text());assert len(a['attempts'])==2
  for attempt in a['attempts']:
   leaf=attempt['outcome']['proof']
   while 'inner' in leaf:leaf=leaf['inner']
   assert leaf['kind']=='finite-closure-v1' and 0<leaf['states']<=200000
 else:assert v['verdict']=='unknown' and r['expired']
result=dict(status='passed',plan_sha256=sha(F/'original-plan.json'),results_sha256=sha(F/'original-results.json'),scope='Full original-input property and two independently checked nested closure proofs; single local diagnostic, no stable speed claim.')
(F/'original-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
