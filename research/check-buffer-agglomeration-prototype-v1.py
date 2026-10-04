"""Finite-grid sanity check of the proposed uniform-weight buffer rule, not a proof."""
import collections,hashlib,itertools,json,resource,time
from pathlib import Path
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
resource.setrlimit(resource.RLIMIT_CPU,(90,90))
start=time.monotonic();deadline=start+90

def fire(marking,tr):
    pre,post=tr
    if any(m<a for m,a in zip(marking,pre)):return None
    return tuple(m-a+b for m,a,b in zip(marking,pre,post))

def reach(initial,transitions):
    queue=collections.deque([initial]);seen={initial:()}
    while queue:
        m=queue.popleft()
        for i,t in enumerate(transitions):
            n=fire(m,t)
            if n is not None and n not in seen:
                assert sum(n)<=sum(initial)
                seen[n]=seen[m]+(i,);queue.append(n)
    return seen

def choices(values):
    return [(t,) for t in values]+[(values[i],values[i+1]) for i in range(len(values)-1)]

def pool(w,mode):
    producers=[];consumers=[]
    if mode=='eager':
        for a,b,c,d in itertools.product(range(3),range(3),range(2),range(2)):
            if a+b>=w+c+d:producers.append(((0,a,b),(w,c,d)))
        consumers=[((w,0,0),(0,a,0)) for a in range(w+1)]
    else:
        producers=[((0,a,0),(w,0,0)) for a in range(w,3)]
        for a,b,c,d in itertools.product(range(2),range(2),range(3),range(3)):
            if w+a+b>=c+d:consumers.append(((w,a,b),(0,c,d)))
    return choices(producers),choices(consumers)

others=[None]+[((0,a,b),(0,c,d)) for a,b,c,d in itertools.product(range(2),repeat=4) if a+b>=c+d]
counts=collections.Counter();states=0
for w,mode in itertools.product([1,2],['eager','delayed']):
    ps,cs=pool(w,mode)
    for producers,consumers,other in itertools.product(ps,cs,others):
        original=list(producers)+list(consumers)+([] if other is None else [other])
        reduced=[];recipes=[]
        for fi,f in enumerate(producers):
            for ci,c in enumerate(consumers):
                pre=tuple(f[0][i]+c[0][i] for i in (1,2))
                post=tuple(f[1][i]+c[1][i] for i in (1,2))
                reduced.append((pre,post));recipes.append((fi,len(producers)+ci))
        if other is not None:
            reduced.append((other[0][1:],other[1][1:]));recipes.append((len(original)-1,))
        for a,b in itertools.product(range(3),repeat=2):
            if time.monotonic()>deadline:raise TimeoutError('prototype grid deadline')
            initial=(0,a,b);left=reach(initial,original);right=reach((a,b),reduced)
            assert {m[2] for m in left}=={m[1] for m in right},(w,mode,original,initial)
            for target,trace in right.items():
                m=initial
                for t in trace:
                    for original_id in recipes[t]:
                        m=fire(m,original[original_id]);assert m is not None
                assert m[1:]==target and m[0]==0
            counts[f'{mode}-weight{w}']+=1;states+=len(left)+len(right)
p=Path('research/buffer-agglomeration-prototype-v1-results.json')
report=dict(status='passed',cases=dict(counts),total_cases=sum(counts.values()),explored_markings=states,elapsed_seconds=time.monotonic()-start,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),scope='Complete finite reachability for the specified nonincreasing-total three-place grid, initial nonbuffer counts0..2, target observation on third place. All singleton producer/consumer choices plus adjacent pairs, and zero/one extra transition. Original and reduced observable reachability sets match; every stored reduced witness replayed through macro recipes. This is a prototype sanity check, not a general proof, Rust implementation, or performance result.')
with p.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(report,indent=2))
