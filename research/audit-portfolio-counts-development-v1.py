"""Audit complete canonical-input matrix, deadlines, identities and validation receipts."""
from pathlib import Path
from collections import Counter
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];HERE=ROOT/'research/portfolio-counts-development-v1';OUT=ROOT/'results/portfolio-counts-development-v1';FROZEN=ROOT/'results/solver-portfolio-counts-development-v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    plan=json.loads((HERE/'plan.json').read_text());terminal=json.loads((HERE/'terminal.json').read_text());assert terminal['exit_code']==0 and terminal['rows']==576
    assert json.loads((HERE/'execution.json').read_text())['plan_sha256']==sha(HERE/'plan.json')
    for name,digest in plan['source_sha256'].items():assert sha(FROZEN/'source'/name)==digest,name
    for name,digest in plan['input_sha256'].items():assert sha(ROOT/name)==digest,name
    for name,info in plan['native'].items():assert sha(FROZEN/name)==info['binary_sha256']
    rows=list(map(json.loads,(OUT/'runs.jsonl').read_text().splitlines()))
    assert Counter((r['query'],r['mode']) for r in rows)==Counter((q,m) for q in plan['query_order'] for m in plan['modes'])
    queries={q['name']:q for q in json.loads((ROOT/'benchmarks/mcc2021-development/manifest.json').read_text())['queries']}
    coverage={m:Counter() for m in plan['modes']};truths={};warnings=[];checks=Counter();artifacts={}
    for row in rows:
        name,mode=row['query'],row['mode'];q=queries[name];assert row['kind']==q['kind']
        assert row['verdict'] in ['reachable','unreachable','unknown']
        assert len(row['branches'])<=len(q['branches'])
        branch_verdicts=[]
        for bi,b in enumerate(row['branches']):
            assert b['branch']==bi and b['verdict'] in ['reachable','unreachable','unknown']
            branch_verdicts.append(b['verdict']);prefix=OUT/f'{name}.{mode}.{bi}';log=Path(str(prefix)+'.json')
            assert sha(log)==b['log_sha256'];artifacts[str(log.relative_to(ROOT))]=sha(log)
            cmd=b['command'];is_scheme=mode in ['count-fixed','count-budget']
            assert Path(cmd[0])==(FROZEN/'count_plan_search' if is_scheme else FROZEN/mode if mode in plan['native'] else Path(plan['python']))
            problem=ROOT/'benchmarks/mcc2021-development'/q['branches'][bi]['path']
            flag='--json' if mode in plan['native'] else '--problem'
            assert (cmd[1] if is_scheme else cmd[cmd.index(flag)+1])==str(problem)
            if is_scheme: assert len(cmd)==4 and cmd[3]=={'count-fixed':'fixed','count-budget':'state-budget'}[mode]
            budget=float(cmd[2] if is_scheme else cmd[cmd.index('--seconds')+1]);assert 0<budget<=plan['seconds']
            assert b['resources']['memory_limit_bytes']==plan['sampled_memory_bytes']
            if mode in plan['native']:
                assert cmd[cmd.index('--method')+1]==plan['native'][mode]['engine']
                assert int(cmd[cmd.index('--max-states')+1])==plan['max_states']
            elif not is_scheme:
                assert cmd[1]==str(FROZEN/'source/scripts/accelerated_bmc.py')
                assert cmd[cmd.index('--binary')+1]==str(FROZEN/'accelerated_bmc')
                assert cmd[cmd.index('--mode')+1]==mode
            if b['verdict']!='unknown':
                answer=json.loads(log.read_text());assert answer['verdict']==b['verdict']
                assert b['exit_code']==0 and not b['expired'] and b['wall_seconds']<=budget and not b['resources']['memory_limit_exceeded']
                v=b['validation'];vlog=Path(str(prefix)+'.validation.json');assert sha(vlog)==v['log_sha256']
                artifacts[str(vlog.relative_to(ROOT))]=sha(vlog)
                receipt=json.loads(vlog.read_text());assert receipt['status']=='passed'
                assert v['passed'] and v['exit_code']==0 and not v['expired'] and not v['resources']['memory_limit_exceeded']
                checker='check_backend_answer.py' if mode in plan['native'] or is_scheme else 'check_accelerated_witness.py'
                assert v['command']==[plan['python'],str(FROZEN/'source/scripts'/checker),str(problem),str(log)]
                checks[receipt.get('check','compressed-witness')]+=1
                if mode not in plan['native'] and not is_scheme:
                    assert b['verdict']=='reachable'
                    assert list(map(int,answer['marking']))==list(map(int,receipt['marking']))
            elif b.get('validation') and not b['validation']['passed']:
                warnings.append(dict(query=name,mode=mode,branch=bi,issue='validation did not pass'))
        aggregate='reachable' if 'reachable' in branch_verdicts else ('unreachable' if len(branch_verdicts)==len(q['branches']) and all(v=='unreachable' for v in branch_verdicts) else 'unknown')
        assert row['verdict']==aggregate
        expected=((aggregate=='reachable')==(q['kind']=='EF')) if aggregate!='unknown' else None
        assert row['property_truth']==expected
        if expected is not None:truths.setdefault(name,set()).add(expected)
        coverage[mode][aggregate]+=1
    disagreements=[q for q,values in truths.items() if len(values)>1]
    positive={m:{r['query'] for r in rows if r['mode']==m and r['verdict']=='reachable'} for m in plan['modes']}
    pairs={a+'/'+b:dict(gains=sorted(positive[a]-positive[b]),losses=sorted(positive[b]-positive[a])) for a,b in [('candidate','native-walk'),('candidate','native-frozen')]}
    summary=dict(status='passed' if not disagreements else 'disagreements',properties=192,rows=576,coverage={k:dict(v) for k,v in coverage.items()},positive_pairs=pairs,disagreements=disagreements,warnings=warnings,independent_checks=dict(checks),plan_sha256=sha(HERE/'plan.json'),runs_sha256=sha(OUT/'runs.jsonl'),checked_artifact_sha256=artifacts,scope='Saved bounded independent-validation execution and complete canonical-input development matrix; no second proof execution, original-input performance, stable speed or superiority claim.')
    (HERE/'audit.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='checked_artifact_sha256'}))
    assert not disagreements,'Definitive answer disagreement'

if __name__=='__main__':main()
