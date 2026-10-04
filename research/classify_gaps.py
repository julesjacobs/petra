"""Diagnostic oracle only; Z3 is not used by the native solver."""
import json, pathlib, z3
root=pathlib.Path(__file__).resolve().parents[1]
queries=['d1_disjunct_0','d3_disjunct_1','d4_disjunct_0','d4_disjunct_1','d4_disjunct_2','d4_disjunct_3','e1_disjunct_0','e7_disjunct_0']
records=[]
for name in queries:
 p=json.loads((root/'results/comparison'/f'{name}.json').read_text())
 row={'query':name}
 for domain,ctor in [('rational',z3.Real),('integer',z3.Int)]:
  s=z3.Solver();s.set(timeout=2000)
  x=[ctor('x'+str(t)) for t in range(len(p['transitions']))]
  s.add(*[v>=0 for v in x])
  m=[z3.IntVal(v) for v in p['initial']]
  for t,tr in enumerate(p['transitions']):
   for i,w in tr['pre']:m[i]=m[i]-w*x[t]
   for i,w in tr['post']:m[i]=m[i]+w*x[t]
  s.add(*[v>=0 for v in m])
  for c in p['target']:
   lhs=z3.Sum([a*v for a,v in zip(c['coefficients'],m)])
   s.add(lhs==c['bound'] if c['equality'] else lhs>=c['bound'])
  row[domain]=str(s.check())
 records.append(row)
print(json.dumps(records,indent=2))
