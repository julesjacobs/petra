"""Coverage and resource diagnostics for the complete audited portfolio count-stage comparison."""
import hashlib,json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'research/reduced-bfs-development-v1';O=ROOT/'results/reduced-bfs-development-v1'
a=json.loads((F/'audit.json').read_text());assert a['status']=='passed'
data=(O/'runs.jsonl').read_bytes();assert hashlib.sha256(data).hexdigest()==a['runs_sha256']
rows=[json.loads(line) for line in data.splitlines()];result=dict(scope='One shared-Mac development repeat; resource diagnostics are descriptive, not stable performance evidence.',coverage=a['coverage'],pairs=a['positive_pairs'],methods={})
for mode in a['coverage']:
 selected=[r for r in rows if r['mode']==mode];branches=[b for r in selected for b in r['branches']]
 result['methods'][mode]=dict(properties=len(selected),branches=len(branches),expired=sum(b['expired'] for b in branches),memory_limit=sum(b['resources']['memory_limit_exceeded'] for b in branches),largest_sampled_rss=max((b['resources'].get('sampled_peak_rss_bytes',0) for b in branches),default=0),reasons=dict(Counter(str(b.get('reason')) for b in branches)))
result['definitive_pairs']={}
for baseline in ['native-counts','native-walk','native-frozen']:
 candidate={r['query']:r['verdict'] for r in rows if r['mode']=='candidate'}
 control={r['query']:r['verdict'] for r in rows if r['mode']==baseline}
 result['definitive_pairs']['candidate/'+baseline]=dict(gains=[dict(query=q,verdict=candidate[q]) for q in sorted(candidate) if candidate[q]!='unknown' and control[q]=='unknown'],losses=[dict(query=q,verdict=control[q]) for q in sorted(candidate) if candidate[q]=='unknown' and control[q]!='unknown'])
(F/'diagnostics.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['coverage','definitive_pairs']}))
