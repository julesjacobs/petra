"""Summarize saved user-space counters, conditional on two definitive answers."""
import hashlib,json,math,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=Path(__file__).resolve().parent
AUDIT=BASE/'audit.json'
audit=json.loads(AUDIT.read_text());assert audit['status']=='passed'
rows={(r['query'],r['method']):r for r in audit['full_rows']}
checks={(r['query'],r['method']):r for r in audit['row_audits']}
methods=['native-batched','native-frozen','verifypn-default','smpt-full-portable']
queries=sorted({q for q,m in rows})
result={}
for method in methods:
 accepted=[];excluded=[]
 for query in queries:
  left,right=rows[query,'native-walk'],rows[query,method]
  if any(r['verdict'] not in ('reachable','unreachable') for r in [left,right]):
   excluded.append(dict(query=query,reason='not-both-definitive'));continue
  assert left['verdict']==right['verdict']
  if any(checks[query,m].get('perf',{}).get('instructions:u')!='full-coverage' for m in ['native-walk',method]):
   excluded.append(dict(query=query,reason='counter-not-full-coverage'));continue
  a=left['resources']['perf_counters']['instructions:u']['value']
  b=right['resources']['perf_counters']['instructions:u']['value']
  if a<=0 or b<=0:
   excluded.append(dict(query=query,reason='nonpositive-counter'));continue
  accepted.append(dict(query=query,verdict=left['verdict'],native_instructions=a,comparison_instructions=b,ratio=a/b))
 groups={}
 for group in ['all','reachable','unreachable']:
  selected=[r for r in accepted if group=='all' or r['verdict']==group]
  if selected:
   ratios=[r['ratio'] for r in selected]
   groups[group]=dict(pairs=len(selected),median_native_over_comparison=statistics.median(ratios),geometric_mean_native_over_comparison=math.exp(statistics.mean(math.log(r) for r in ratios)),native_fewer_instructions=sum(r<1 for r in ratios))
 result[method]=dict(groups=groups,pairs=accepted,excluded=excluded)
report=dict(audit_sha256=hashlib.sha256(AUDIT.read_bytes()).hexdigest(),metric='instructions:u, timed solver only; independent checking excluded',scope='One repeat; conditional on both definitive and counters with100%running coverage. Excluded queries retained. Includes duplicates. Ratios are not unconditional speedups; deadlines, workload scheduling and different proof obligations can change executed work.',comparisons=result)
(BASE/'instruction-summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({m:v['groups'] for m,v in result.items()},indent=2))
