"""Audit the combined portfolio's independently checked original-input gap cases."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'research/portfolio-reduced-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((F/'original-plan.json').read_text());rows=json.loads((F/'original-results.json').read_text())
for name,d in p['source_sha256'].items():assert sha(F/'snapshot/source'/name)==d,name
for name,d in p['input_sha256'].items():assert sha(Path(name))==d,name
assert sha(F/'snapshot/vass-reach')==p['pins']['research/portfolio-reduced-v1/snapshot/vass-reach']
assert [(r['query'],r['method']) for r in rows]==[(q['name'],m) for q in p['queries'] for m in p['methods']]
for r in rows:
 log=F/(r['query']+'.'+r['method']+'.original.json');assert sha(log)==r['log_sha256']
 v=r['validation'];check=v['validation']
 assert check['exit_code']==0 and not check['outer_timeout'] and not check['resources']['memory_limit_exceeded']
 if r['query'].startswith('RefineWMG'):expected='reachable'
 else:expected='unreachable' if r['method']=='portfolio-reduced' else 'unknown'
 assert v['verdict']==expected
 if expected!='unknown':
  assert r['exit_code']==0 and not r['expired'] and not r['resources']['memory_limit_exceeded'] and r['wall']<p['seconds']
  assert not v['deadline_exceeded'] and v['translation_check']=='independent-original-input-equals-all-canonical-branches'
  if expected=='reachable':assert v['independent_checks']==['python-witness']
  else:
   assert [b['branch'] for b in v['branches']]==[0,1]
   assert v['independent_checks']==['python-buffer-agglomeration']*2
result=dict(status='passed',rows=4,plan_sha256=sha(F/'original-plan.json'),results_sha256=sha(F/'original-results.json'),scope='Saved original-input validation and source identities; two diagnosed development properties, no whole-cohort or stable speed claim.')
(F/'original-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
