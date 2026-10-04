from pathlib import Path
from collections import Counter
import json
ROOT=Path(__file__).resolve().parents[1];folder=ROOT/'research/abmc-mcc-sparse-v1';corpus=ROOT/'benchmarks/mcc2021-development'
audit=json.loads((folder/'audit.json').read_text());assert audit['status']=='passed'
rs=[json.loads(line) for line in (ROOT/'results/abmc-mcc-sparse-v1/runs.jsonl').read_text().splitlines()]
initial=set()
for q in json.loads((corpus/'manifest.json').read_text())['queries']:
 for b in q['branches']:
  p=json.loads((corpus/b['path']).read_text())
  if all((sum(a*m for a,m in zip(c['coefficients'],p['initial']))==c['bound']) if c['equality'] else (sum(a*m for a,m in zip(c['coefficients'],p['initial']))>=c['bound']) for c in p['target']):initial.add(q['name']);break
summary=dict(initial_positive_properties=len(initial),methods={})
for mode in ['ordinary','singleton','cycles','native-walk','native-frozen']:
 rows=[r for r in rs if r['mode']==mode];pos={r['query'] for r in rows if r['verdict']=='reachable'}
 summary['methods'][mode]=dict(noninitial_positives=len(pos-initial),initial_positives=len(pos&initial),branch_reasons=Counter(str(b.get('reason')) for r in rows for b in r['branches']))
union={r['query'] for r in rs if r['mode'] in ['ordinary','singleton','cycles'] and r['verdict']=='reachable'}
native={r['query'] for r in rs if r['mode']=='native-walk' and r['verdict']=='reachable'}
summary.update(bmc_diagnostic_union=len(union),bmc_union_gains_over_native_walk=sorted(union-native))
(folder/'diagnostics.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary))
