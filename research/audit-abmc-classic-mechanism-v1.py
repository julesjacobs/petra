"""Audit complete frozen mechanism matrix and independently recheck positives."""
from pathlib import Path
from collections import Counter
import hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/abmc-classic-mechanism-v1';FROZEN=ROOT/'results/solver-accelerated-bmc-v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    plan=json.loads((OUT/'plan.json').read_text());terminal=json.loads((OUT/'terminal.json').read_text())
    assert terminal==dict(exit_code=0,rows=111)
    assert sha(FROZEN/'accelerated_bmc')==plan['binary_sha256']
    for name,digest in plan['source_sha256'].items():assert sha(FROZEN/'source'/name)==digest,name
    for name,digest in plan['input_sha256'].items():assert sha(ROOT/name)==digest,name
    rows=list(map(json.loads,(OUT/'runs.jsonl').read_text().splitlines()))
    assert Counter((r['query'],r['mode']) for r in rows)==Counter((q,m) for q in plan['query_order'] for m in plan['modes'])
    queries={q['name']:q for q in json.loads((ROOT/'benchmarks/smpt-classic/manifest.json').read_text())['queries']}
    verified=0;issues=[];reasons=Counter()
    # Saved bounded independent validation is audited here; no unbounded proof replay.
    for row in rows:
        assert row['kind']==queries[row['query']]['kind']
        assert row['verdict'] in ('reachable','unknown')
        positives=0
        for branch in row['branches']:
            bi=branch['branch'];assert bi<len(queries[row['query']]['branches'])
            prefix=f"{row['query']}.{row['mode']}.{bi}"
            reasons[(row['mode'],str(branch.get('reason')))]+=1
            if branch.get('validation'):
                check=branch['validation'];p=OUT/(prefix+'.validation.json')
                if check['exit_code']==0 and not check['expired']:
                    assert json.loads(p.read_text())['status']=='passed'
                    answer=json.loads((OUT/(prefix+'.json')).read_text());assert answer['verdict']=='reachable'
                    assert not branch['expired'] and branch['exit_code']==0 and not branch['resources']['memory_limit_exceeded']
                    assert not branch.get('late_answer')
                    assert check['command'][1]==str(FROZEN/'source/scripts/check_accelerated_witness.py')
                    assert list(map(int,answer['marking']))==list(map(int,json.loads(p.read_text())['marking']))
                    positives+=1
        if row['verdict']=='reachable':
            assert positives==1 and row['property_truth']==(row['kind']=='EF')
            verified+=1
        else:assert row['property_truth'] is None
    solved={m:[r['query'] for r in rows if r['mode']==m and r['verdict']=='reachable'] for m in plan['modes']}
    pairwise={}
    for left,right in [('cycles','singleton'),('cycles','ordinary'),('singleton','ordinary')]:
        pairwise[left+'/'+right]=dict(gains=sorted(set(solved[left])-set(solved[right])),losses=sorted(set(solved[right])-set(solved[left])))
    summary=dict(status='passed',properties=37,rows=len(rows),checked_positive_rows=verified,reachable_by_mode={m:len(v) for m,v in solved.items()},solved=solved,pairwise=pairwise,branch_reasons=[dict(mode=m,reason=r,count=c) for (m,r),c in sorted(reasons.items())],plan_sha256=sha(OUT/'plan.json'),runs_sha256=sha(OUT/'runs.jsonl'),scope='One-second positive-witness development screen on all37canonical classical properties. No unreachability method, competitor result, stable speed claim or publication evidence. Audit checks saved bounded independent-validation outputs, not a second proof execution.')
    (OUT/'audit.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary))

if __name__=='__main__':main()
