#!/usr/bin/env python3
"""Direct bounded-model baseline for raw queries, without complement/DNF preprocessing."""
import argparse,json,time,z3
p=argparse.ArgumentParser();p.add_argument('query');p.add_argument('--seconds',type=float,default=2);a=p.parse_args()
q=json.load(open(a.query));deadline=time.monotonic()+a.seconds
solver=z3.Solver(); states=[]; choices=[]
def marking(k):
    xs=[z3.Int(f'm{k}_{i}') for i in range(len(q['places']))]
    solver.add(*[x>=0 for x in xs]);states.append(xs);return xs
m=marking(0);solver.add(*[x==v for x,v in zip(m,q['initial'])])
def target(m,k):
    union=[]
    for j,c in enumerate(q['target']['excluded_semilinear']):
        ns=[z3.Int(f'n{k}_{j}_{i}') for i in range(len(c['periods']))]
        base=dict(c['base']);periods=list(map(dict,c['periods']))
        body=z3.And(*[n>=0 for n in ns],*[m[i]==base.get(i,0)+sum(n*v.get(i,0) for n,v in zip(ns,periods)) for i in q['target']['response_places']])
        union.append(z3.Exists(ns,body) if ns else body)
    return z3.And(*[m[i]==0 for i in q['target']['zero_places']],z3.Not(z3.Or(*union)))
for depth in range(10000):
    remaining=deadline-time.monotonic()
    if remaining<=0:break
    solver.set(timeout=max(1,int(remaining*1000)));solver.push();solver.add(target(m,depth))
    answer=solver.check()
    if answer==z3.sat:
        model=solver.model();trace=[model.eval(x).as_long() for x in choices]
        print(json.dumps(dict(verdict='reachable',method='raw-z3',trace=trace,marking=[model.eval(x).as_long() for x in m],states=depth)));break
    solver.pop()
    if answer==z3.unknown:break
    prev=m;m=marking(depth+1);choice=z3.Int(f't{depth}');choices.append(choice)
    options=[]
    for t,tr in enumerate(q['transitions']):
        pre,post=dict(tr['pre']),dict(tr['post'])
        options.append(z3.And(choice==t,*[prev[i]>=w for i,w in tr['pre']],*[m[i]==prev[i]-pre.get(i,0)+post.get(i,0) for i in range(len(m))]))
    solver.add(z3.Or(*options))
else:depth=10000
if answer!=z3.sat:print(json.dumps(dict(verdict='unknown',method='raw-z3',reason='bounded search exhausted or limited',states=depth)))
