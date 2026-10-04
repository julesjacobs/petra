"""Identify bounded BFS runs that never leave their initial word layer."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
f=ROOT/'research/native-scheme-development-v2'
assert json.loads((f/'audit.json').read_text())['status']=='passed'
d=json.loads((f/'diagnostics.json').read_text());report={}
for mode in ['native-singleton','native-cycles']:
 samples=d['methods'][mode]['samples']
 roots=[r for r in samples if r['verdict']=='unknown' and 0<r['statistics']['schemes']<=r['statistics']['words']]
 report[mode]=dict(unknown_root_only_branches=len(roots),unknown_branches_with_statistics=sum(r['verdict']=='unknown' for r in samples),attempts=sum(r['statistics']['schemes'] for r in roots),prefix_refutations=sum(r['statistics']['prefix_refutations'] for r in roots),branches=[dict(query=r['query'],branch=r['branch']) for r in roots])
(f/'root-diagnosis.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({m:{k:v for k,v in r.items() if k!='branches'} for m,r in report.items()}))
