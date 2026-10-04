"""Differentially check real Z3 encodings against bounded exact exploration."""
from pathlib import Path
import hashlib,json,subprocess,tempfile
from collections import deque
ROOT=Path(__file__).resolve().parents[1]
EXAMPLE=ROOT/'target/debug/examples/accelerated_bmc'
Z3=ROOT/'vendor/venv/bin/z3'

def accepts(p,m):
    return all((sum(a*b for a,b in zip(c['coefficients'],m))==c['bound']) if c['equality'] else (sum(a*b for a,b in zip(c['coefficients'],m))>=c['bound']) for c in p['target'])

def fire(t,m):
    if any(m[i]<w for i,w in t['pre']):return None
    n=list(m)
    for i,w in t['pre']:n[i]-=w
    for i,w in t['post']:n[i]+=w
    return tuple(n)

def exhaustive(p):
    start=tuple(p['initial']); seen={start}; queue=deque([start])
    while queue:
        m=queue.popleft()
        if accepts(p,m):return True
        for t in p['transitions']:
            n=fire(t,m)
            if n is not None and n not in seen:seen.add(n);queue.append(n)
    return False

def check_compressed(p,segments):
    m=list(p['initial'])
    for segment in segments:
        n=int(segment['repetitions']); assert n>=0
        if n==0:continue
        # Each individual guard must hold at both extreme repetition indices.
        offset=[0]*len(m); guards=[]
        for index in segment['word']:
            t=p['transitions'][index]
            guards.extend((i,w-offset[i]) for i,w in t['pre'])
            for i,w in t['pre']:offset[i]-=w
            for i,w in t['post']:offset[i]+=w
        for i,w in guards:assert min(m[i],m[i]+(n-1)*offset[i])>=w
        m=[x+n*d for x,d in zip(m,offset)]
        assert min(m,default=0)>=0
    assert accepts(p,m)
    return m

def run(p,words,depth,expected):
    with tempfile.TemporaryDirectory(prefix='pvass-abmc-') as tmp:
        d=Path(tmp); (d/'p.json').write_text(json.dumps(p)); (d/'w.json').write_text(json.dumps(words))
        args=[str(EXAMPLE),'emit',str(d/'p.json'),str(d/'w.json'),str(depth)]
        formula=subprocess.run(args,text=True,capture_output=True,check=True,timeout=10).stdout
        result=subprocess.run([str(Z3),'-in','-T:5'],input=formula,text=True,capture_output=True,timeout=10)
        status=result.stdout.splitlines()[0]; assert status in ['sat','unsat'],result
        assert (status=='sat')==expected,(p,words,depth,result.stdout)
        (d/'model').write_text(result.stdout)
        args[1]='check'; args.append(str(d/'model'))
        answer=json.loads(subprocess.run(args,text=True,capture_output=True,check=True,timeout=10).stdout)
        if expected:
            assert answer['verdict']=='reachable'
            marking=check_compressed(p,answer['segments']); assert list(map(int,answer['marking']))==marking
        else:assert answer['verdict']=='unknown'
        return dict(status=status,formula_sha256=hashlib.sha256(formula.encode()).hexdigest())

def main():
    rows=[]
    for total in range(6):
        for guard in [1,2,3]:
            for target in range(total+1):
                p=dict(places=['p','q'],initial=[total,0],transitions=[dict(name='forward',pre=[[0,guard]],post=[[0,guard-1],[1,1]] if guard>1 else [[1,1]]),dict(name='backward',pre=[[1,1]],post=[[0,1]])],target=[dict(coefficients=[-1,1],bound=2*target-total,equality=True)])
                rows.append(run(p,[[0],[1],[0,1]],2,exhaustive(p)))
    p=dict(places=['p'],initial=[0],transitions=[dict(name='produce',pre=[],post=[[0,1]]),dict(name='read',pre=[[0,2]],post=[[0,2]])],target=[dict(coefficients=[1],bound=1,equality=False)])
    rows.append(run(p,[[0,1]],2,False))
    p['target'][0]['bound']=10**12
    rows.append(run(p,[[0]],1,True))
    p['target'][0]['bound']=0
    rows.append(run(p,[],0,True))
    record=dict(status='passed',queries=len(rows),sat=sum(r['status']=='sat' for r in rows),rows=rows,z3_version=subprocess.check_output([str(Z3),'--version'],text=True).strip(),source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'src/accelerated_bmc.rs',ROOT/'examples/accelerated_bmc.rs',Path(__file__)]})
    (ROOT/'research/accelerated-bmc-prototype-check.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({k:v for k,v in record.items() if k not in ['rows','source_sha256']}))

if __name__=='__main__':main()
