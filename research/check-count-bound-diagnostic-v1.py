"""Independently check a firing-count cap refutation against original Petri arcs."""
import hashlib,json
from fractions import Fraction
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'research/verifypn-gap-diagnostics-v1'
pfile=ROOT/'benchmarks/general-development-v3/RefineWMG-PT-100101__RC11/branch-4.json'
cfile=F/'count-bound-8192.json';p=json.loads(pfile.read_text());c=json.loads(cfile.read_text())
assert c['status']=='cap-refuted'
effect=[{} for _ in p['places']]
for t,tr in enumerate(p['transitions']):
 for place,w in tr['pre']:effect[place][t]=effect[place].get(t,0)-w
 for place,w in tr['post']:effect[place][t]=effect[place].get(t,0)+w
rows=[(dict(a),-m) for a,m in zip(effect,p['initial'])]
for target in p['target']:
 a={};b=target['bound']
 for place,w in enumerate(target['coefficients']):
  if not w:continue
  b-=w*p['initial'][place]
  for t,d in effect[place].items():a[t]=a.get(t,0)+w*d
 if target['equality']:rows.append(({t:-x for t,x in a.items()},-b))
 rows.append((a,b))
rows.append(({t:-1 for t in range(len(p['transitions']))},-c['cap']))
lhs=[Fraction(0) for _ in p['transitions']];rhs=Fraction(0);used=set();cap_weight=Fraction(0)
used_targets=[]
for index,weight in c['multipliers']:
 assert type(index) is int and 0<=index<len(rows) and index not in used
 used.add(index);q=Fraction(weight);assert q>0
 a,b=rows[index]
 for t,x in a.items():lhs[t]+=q*x
 rhs+=q*b
 if index==len(rows)-1:cap_weight=q
 elif index>=len(p['places']):used_targets.append(index-len(p['places']))
assert all(x<=0 for x in lhs) and rhs>0
assert cap_weight>0
lower=Fraction(c['cap'])+rhs/cap_weight
ceiling=-((-lower.numerator)//lower.denominator)
record=dict(status='passed',scope='Necessary total-firing lower bound; not a global unreachability proof.',cap=c['cap'],rational_lower_bound=str(lower),integer_lower_bound=ceiling,used_target_rows=used_targets,contradiction_rhs=str(rhs),inputs={str(q.relative_to(ROOT)):hashlib.sha256(q.read_bytes()).hexdigest() for q in [pfile,cfile,Path(__file__)]})
(F/'count-bound-check.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
