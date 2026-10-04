"""Bounded exploratory pair abstraction; emits no accepted solver verdict."""
import argparse, hashlib, json, time
from pathlib import Path


def analyze(path, seconds):
    data=path.read_bytes(); p=json.loads(data); n=len(p['places']); start=time.monotonic(); deadline=start+seconds
    parent=list(range(n))
    def find(x):
        while x!=parent[x]:parent[x]=parent[parent[x]];x=parent[x]
        return x
    transitions=[]
    for t in p['transitions']:
        pre=dict(t['pre']);post=dict(t['post']);delta={i:post.get(i,0)-pre.get(i,0) for i in pre.keys()|post.keys()}
        changed=[i for i,d in delta.items() if d]
        if changed:
            root=find(changed[0])
            for i in changed[1:]:parent[find(i)]=root
        transitions.append((pre,post))
    groups={}
    for i in range(n):groups.setdefault(find(i),[]).append(i)
    masses={root:sum(p['initial'][i] for i in g) for root,g in groups.items()}
    certified=all(m==1 for m in masses.values())
    for pre,post in transitions:
        effects={}
        for sign,arcs in [(-1,pre),(1,post)]:
            for i,w in arcs.items():effects[find(i)]=effects.get(find(i),0)+sign*w
        certified &= all(d==0 for d in effects.values())
    result=dict(input=str(path),sha256=hashlib.sha256(data).hexdigest(),places=n,transitions=len(transitions),safe_components=len(groups),certified_safe=certified)
    if not certified:return result|dict(status='unsupported-safety')
    activity={root:0 for root in groups}
    for pre,post in transitions:
        for root in {find(i) for i in pre.keys()|post.keys() if pre.get(i,0)!=post.get(i,0)}:activity[root]+=1
    chosen=min((count,root) for root,count in activity.items() if count)[1]
    result['landmark_component']=groups[chosen]
    result['landmark_transitions']=activity[chosen]
    initial=sum(1<<i for i,x in enumerate(p['initial']) if x)
    active=[initial,0]
    rows=[[initial if p['initial'][i] else 0 for i in range(n)],[0 for _ in range(n)]]
    encoded=[]
    for pre,post in transitions:
        if any(w>1 for w in pre.values()):continue
        # A safe net cannot enable an arc producing more than one token.
        if any(w>1 for w in post.values()):continue
        landmark=any(find(i)==chosen and pre.get(i,0)!=post.get(i,0) for i in pre.keys()|post.keys())
        encoded.append((tuple(pre),tuple(post),sum(1<<i for i in pre.keys()-post.keys()),landmark))
    passes=0;added=0;checks=0
    while True:
        changed=False;passes+=1
        for phase in range(2):
          for pre,post,deleted,landmark in encoded:
            checks+=1
            if checks%256==0 and time.monotonic()>=deadline:
                return result|dict(status='timeout',passes=passes,checks=checks,added_pairs=added,seconds=time.monotonic()-start)
            if any(not (active[phase]>>i)&1 for i in pre):continue
            if any(not (rows[phase][i]>>j)&1 for i in pre for j in pre):continue
            compatible=active[phase]
            for i in pre:compatible &= rows[phase][i]
            compatible &= ~deleted
            destination=1 if landmark else phase
            if destination!=phase:
                remaining=compatible
                while remaining:
                    bit=remaining & -remaining;remaining-=bit;i=bit.bit_length()-1
                    copied=rows[phase][i] & compatible
                    fresh=copied & ~rows[destination][i]
                    if fresh:changed=True;added+=fresh.bit_count();rows[destination][i]|=copied
                active[destination] |= compatible
            for i in post:compatible |= 1<<i
            for i in post:
                fresh=compatible & ~rows[destination][i]
                if fresh:
                    changed=True;added+=fresh.bit_count();rows[destination][i]|=compatible
                    while fresh:
                        bit=fresh & -fresh;fresh-=bit;j=bit.bit_length()-1
                        rows[destination][j] |= 1<<i
                active[destination] |= 1<<i
        if not changed:break
    required=set()
    for target in p['target']:
        for sign in ([1,-1] if target['equality'] else [1]):
            coeff=[sign*c for c in target['coefficients']];bound=sign*target['bound'];maximum=sum(max(0,c) for c in coeff)
            for i,c in enumerate(coeff):
                if c>0 and maximum-c<bound:required.add(i)
    conflicts=[[(p['places'][i],p['places'][j]) for i in sorted(required) for j in sorted(required) if i<=j and not ((rows[phase][i]>>j)&1)] for phase in range(2)]
    return result|dict(status='closed',passes=passes,checks=checks,added_pairs=added,seconds=time.monotonic()-start,required=[p['places'][i] for i in sorted(required)],excluded_required_pairs_by_phase=conflicts,scope='Exploratory closure only; requires an independent checker before an accepted verdict.')

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('queries',nargs='+',type=Path);a.add_argument('--seconds',type=float,default=30);args=a.parse_args()
    for q in args.queries:print(json.dumps(analyze(q,args.seconds)),flush=True)
