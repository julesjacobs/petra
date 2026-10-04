#!/usr/bin/env python3
"""Whole raw-query benchmarks; original-net replay plus independent Z3 membership checks."""
import argparse,collections,hashlib,json,pathlib,statistics,subprocess,time
from benchmark import run
ROOT=pathlib.Path(__file__).resolve().parents[1]
def verify(q,a):
    import z3
    assert a['verdict']=='reachable'
    m=q['initial'][:]
    for i in a['trace']:
        assert type(i) is int and 0<=i<len(q['transitions']);t=q['transitions'][i]
        for j,w in t['pre']:assert m[j]>=w
        for j,w in t['pre']:m[j]-=w
        for j,w in t['post']:m[j]+=w
    assert m==a['marking']
    assert all(m[i]==0 for i in q['target']['zero_places'])
    for j,c in enumerate(q['target']['excluded_semilinear']):
        base=dict(c['base']);vs=list(map(dict,c['periods']));ns=[z3.Int(f'n{i}') for i in range(len(vs))]
        solver=z3.Solver();solver.set(timeout=10000);solver.add(*[n>=0 for n in ns])
        solver.add(*[m[i]==base.get(i,0)+sum(n*v.get(i,0) for n,v in zip(ns,vs)) for i in q['target']['response_places']])
        assert solver.check()==z3.unsat, f'component {j} membership not refuted'
    return 'python-replay-z3-nonmembership'
p=argparse.ArgumentParser();p.add_argument('--corpus',default='benchmarks/raw-harder');p.add_argument('--output',default='results/raw-initial');p.add_argument('--methods',nargs='+',default=['raw-bfs','raw-search']);p.add_argument('--seconds',type=float,default=2);p.add_argument('--repeat',type=int,default=1);p.add_argument('--filter',default='');p.add_argument('--binary',default='target/release/vass-reach');a=p.parse_args()
import re
out=ROOT/a.output;out.mkdir(parents=True,exist_ok=True);binary=ROOT/a.binary
manifest=json.loads((ROOT/a.corpus/'collection.json').read_text());queries=[r for r in manifest['sources'] if r['status']=='exported' and (not a.filter or re.search(a.filter,r['name']))]
(out/'environment.json').write_text(json.dumps(dict(corpus=a.corpus,queries=len(queries),seconds=a.seconds,repeat=a.repeat,methods=a.methods,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),source_sha256={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in (ROOT/'src').glob('*.rs')},scope='One original net and uncomplemented semilinear target per program. No DNF splitting. Sequential processes; proof verification outside timing.'),indent=2))
rows=[]
with (out/'runs.jsonl').open('w') as records:
 for item in queries:
    path=ROOT/a.corpus/item['name']/'query.json';q=json.loads(path.read_text());digest=hashlib.sha256(path.read_bytes()).hexdigest();assert digest==item['query_sha256']
    for repeat in range(a.repeat):
     for method in a.methods if repeat%2==0 else a.methods[::-1]:
        log=out/f'{item["name"]}.{method}.{repeat}.json'
        cmd=[str(ROOT/'vendor/venv/bin/python'),str(ROOT/'scripts/raw_z3.py'),str(path),'--seconds',str(a.seconds)] if method=='raw-z3' else [str(binary),'--raw',str(path),'--method',method,'--seconds',str(a.seconds),'--max-states','200000']
        wall,code,expired=run(cmd,ROOT,a.seconds+2,log)
        r=dict(query=item['name'],method=method,repeat=repeat,sha256=digest,wall_seconds=wall,exit_code=code,outer_timeout=expired,verdict='unknown')
        if not expired:
         try:
            assert code==0;answer=json.loads(log.read_text());r.update({k:v for k,v in answer.items() if k not in ('trace','marking','proof')})
            if r['verdict']=='reachable':r['independent_check']=verify(q,answer)
            else:assert r['verdict']=='unknown'
         except Exception as e:r.update(verdict='error',error=repr(e))
        records.write(json.dumps(r)+'\n');records.flush();rows.append(r);print(r['query'],method,r['verdict'],round(wall,3),flush=True)
lines=['# Whole raw-query comparison','',f'{len(queries)} programs; {a.seconds}s; {a.repeat} repetition(s).','', '| Method | Reachable | Unknown | Errors/unstable |','|---|---:|---:|---:|']
for method in a.methods:
    groups=collections.defaultdict(set)
    for r in rows:
        if r['method']==method:groups[r['query']].add(r['verdict'])
    c=collections.Counter(next(iter(v)) if len(v)==1 else 'unstable' for v in groups.values());lines.append(f'| {method} | {c["reachable"]} | {c["unknown"]} | {c["error"]+c["unstable"]} |')
lines+=['','Unknown includes all safe instances unless an engine implements a negative proof. A raw query has an entire semilinear-complement target; counts are not comparable to old per-disjunct coverage. raw-z3 is a new direct quantified BMC baseline, not SMPT. All positives are independently replayed and checked against each excluded linear set with Z3 outside timing.']
(out/'REPORT.md').write_text('\n'.join(lines)+'\n')
