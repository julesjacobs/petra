"""Canonical-input development comparison with two frozen native controls."""
from pathlib import Path
import argparse,hashlib,json,random,shutil,sys,time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from process_runner import run,workspace_workloads
HERE=ROOT/'research/portfolio-reduced-development-v1'
CORPUS=ROOT/'benchmarks/mcc2021-development'
OUT=ROOT/'results/portfolio-reduced-development-v1'
FROZEN=ROOT/'results/solver-portfolio-reduced-development-v1'
NATIVE={'candidate':('unused','portfolio-reduced'),'native-counts':('unused','portfolio-walk-counts'),'native-walk':('solver-walk-sparse-v1','portfolio-walk'),'native-frozen':('solver-repeated-search-v1','portfolio-batched')}
MODES=list(NATIVE)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def command(mode,problem,seconds,artifacts):
    return [str(FROZEN/mode),'--json',str(problem),'--method',NATIVE[mode][1],'--seconds',str(seconds),'--max-states','2000000']

def prepare():
    assert not FROZEN.exists() and not (HERE/'plan.json').exists()
    assert not workspace_workloads(ROOT)
    queries=json.loads((CORPUS/'manifest.json').read_text())['queries'];assert len(queries)==192 and all(q['status']=='imported' for q in queries)
    inputs={str((CORPUS/'manifest.json').relative_to(ROOT)):sha(CORPUS/'manifest.json')}
    for q in queries:
        for b in q['branches']:
            p=CORPUS/b['path'];assert sha(p)==b['sha256'];inputs[str(p.relative_to(ROOT))]=b['sha256']
    paths=list((ROOT/'src').glob('*.rs'))+list((ROOT/'scripts').glob('*.py'))+[ROOT/'Cargo.toml',ROOT/'Cargo.lock',ROOT/'tests/reduced_bfs.rs',ROOT/'tests/count_cap.rs',Path(__file__)]
    paths += [p for p in (ROOT/'vendor/varisat').rglob('*') if p.is_file() and '.git' not in p.parts and 'target' not in p.parts]
    FROZEN.mkdir();pins={}
    for p in paths:
        dest=FROZEN/'source'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest);pins[str(p.relative_to(ROOT))]=sha(p)
    native={}
    for label,(folder,engine) in NATIVE.items():
        if label=='candidate':
            p=ROOT/'target/release/vass-reach'
            expected=json.loads((ROOT/'research/portfolio-reduced-v1/original-plan.json').read_text())['pins']['research/portfolio-reduced-v1/snapshot/vass-reach']
            assert sha(p)==expected
            shutil.copy2(p,FROZEN/label)
            native[label]=dict(binary_sha256=sha(p),engine=engine,original=str(p.relative_to(ROOT)))
        elif label=='native-counts':
            p=ROOT/'results/solver-portfolio-counts-development-v1/candidate'
            old=json.loads((ROOT/'research/portfolio-counts-development-v1/plan.json').read_text())
            assert sha(p)==old['native']['candidate']['binary_sha256']
            shutil.copy2(p,FROZEN/label)
            native[label]=dict(binary_sha256=sha(p),engine=engine,original=str(p.relative_to(ROOT)))
        else:
            p=ROOT/'results'/folder;provenance=json.loads((p/'provenance.json').read_text());assert sha(p/'vass-reach')==provenance['binary_sha256']
            shutil.copy2(p/'vass-reach',FROZEN/label)
            native[label]=dict(binary_sha256=sha(FROZEN/label),engine=engine,original=str(p.relative_to(ROOT)),provenance_sha256=sha(p/'provenance.json'))
    a=json.loads((ROOT/'results/solver-walk-sparse-v1/source-files-sha256.json').read_text());b=json.loads((ROOT/'results/solver-walk-sparse-v2/source-files-sha256.json').read_text());assert all(b.get(k)==v for k,v in a.items())
    random.Random(2026092805).shuffle(queries)
    plan=dict(properties=192,rows=768,modes=MODES,seconds=1.,repeat=1,order_seed=2026092805,query_order=[q['name'] for q in queries],input_sha256=inputs,source_sha256=pins,native=native,python=sys.executable,sampled_memory_bytes=2**31,checker_seconds=30,max_states=2000000,scope='Complete192 canonical-input development cohort. Shared1s per property across branches; one Mac repeat, sampled2GiB; independent checking outside timing. Walk-count portfolio plus bounded reduced BFS stage (200k-state cap within this stage) vs three frozen native portfolios; no held-out/general superiority claim.')
    (HERE/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    print(json.dumps(dict(status='prepared',rows=768,plan_sha256=sha(HERE/'plan.json'))))

def verify_pins(plan):
    for name,digest in plan['source_sha256'].items():assert sha(FROZEN/'source'/name)==digest,name
    for name,digest in plan['input_sha256'].items():assert sha(ROOT/name)==digest,name
    for name,info in plan['native'].items():assert sha(FROZEN/name)==info['binary_sha256']

def validate(mode,problem,answer,prefix,seconds):
    checker='check_backend_answer.py'
    cmd=[sys.executable,str(FROZEN/'source/scripts'/checker),str(problem),str(answer)]
    log=Path(str(prefix)+'.validation.json')
    wall,code,expired,resources=run(cmd,ROOT,seconds,log,2**31)
    try:receipt=json.loads(log.read_text())
    except ValueError:receipt={}
    valid=code==0 and not expired and not resources['memory_limit_exceeded'] and receipt.get('status')=='passed'
    return valid,dict(wall_seconds=wall,exit_code=code,expired=expired,resources=resources,command=cmd,log_sha256=sha(log),passed=valid)

def smoke(plan):
    verify_pins(plan);assert not workspace_workloads(ROOT)
    folder=HERE/'smoke';folder.mkdir()
    rows=[]
    for positive in [False,True]:
        problem=folder/('positive.json' if positive else 'negative.json')
        problem.write_text(json.dumps(dict(places=['p'],initial=[0],transitions=[dict(name='produce',pre=[],post=[[0,1]])] if positive else [],target=[dict(coefficients=[1],bound=2,equality=True)])))
        for mode in MODES:
            prefix=folder/f'{problem.stem}.{mode}';log=Path(str(prefix)+'.json')
            wall,code,expired,resources=run(command(mode,problem,3,Path(str(prefix)+'.artifacts')),ROOT,3,log,2**31)
            assert code==0 and not expired
            answer=json.loads(log.read_text());expected='reachable' if positive else ('unreachable' if mode in NATIVE else 'unknown')
            assert answer['verdict']==expected,(mode,answer)
            if expected!='unknown':
                passed,receipt=validate(mode,problem,log,prefix,30);assert passed,(mode,receipt)
            rows.append(dict(mode=mode,positive=positive,verdict=expected,log_sha256=sha(log)))
    (HERE/'smoke.json').write_text(json.dumps(dict(status='passed',plan_sha256=sha(HERE/'plan.json'),rows=rows),indent=2)+'\n')
    print('smoke passed',len(rows),flush=True)

def launch(plan):
    verify_pins(plan);assert not workspace_workloads(ROOT)
    smoke_receipt=json.loads((HERE/'smoke.json').read_text());assert smoke_receipt['status']=='passed' and smoke_receipt['plan_sha256']==sha(HERE/'plan.json')
    assert not OUT.exists() and not (HERE/'execution.json').exists()
    OUT.mkdir();(HERE/'execution.json').write_text(json.dumps(dict(status='running',plan_sha256=sha(HERE/'plan.json'),started=time.time())))
    qs={q['name']:q for q in json.loads((CORPUS/'manifest.json').read_text())['queries']}
    for qi,name in enumerate(plan['query_order']):
        q=qs[name];rot=qi%len(MODES)
        for mode in MODES[rot:]+MODES[:rot]:
            started=time.monotonic();checker_wall=0.;branches=[];verdict='unknown';remaining=plan['seconds']
            for bi,b in enumerate(q['branches']):
                remaining=plan['seconds']-(time.monotonic()-started-checker_wall)
                if remaining<=0:break
                share=remaining/(len(q['branches'])-bi);problem=CORPUS/b['path'];prefix=OUT/f'{name}.{mode}.{bi}';log=Path(str(prefix)+'.json')
                cmd=command(mode,problem,share,Path(str(prefix)+'.artifacts'))
                wall,code,expired,resources=run(cmd,ROOT,share,log,2**31)
                branch=dict(branch=bi,wall_seconds=wall,exit_code=code,expired=expired,resources=resources,command=cmd,log_sha256=sha(log),verdict='unknown')
                branches.append(branch)
                try:answer=json.loads(log.read_text())
                except ValueError:answer={}
                branch['candidate_verdict']=answer.get('verdict');branch['reason']=answer.get('reason')
                late=time.monotonic()-started-checker_wall>plan['seconds']
                if answer.get('verdict') in ('reachable','unreachable') and code==0 and not expired and wall<=share and not late and not resources['memory_limit_exceeded']:
                    passed,receipt=validate(mode,problem,log,prefix,plan['checker_seconds']);checker_wall+=receipt['wall_seconds'];branch['validation']=receipt
                    if passed:branch['verdict']=answer['verdict']
                if branch['verdict']=='reachable':verdict='reachable';break
            if verdict!='reachable' and len(branches)==len(q['branches']) and all(b['verdict']=='unreachable' for b in branches):verdict='unreachable'
            row=dict(query=name,kind=q['kind'],mode=mode,verdict=verdict,property_truth=((verdict=='reachable')==(q['kind']=='EF')) if verdict!='unknown' else None,solver_wall_seconds=time.monotonic()-started-checker_wall,checker_wall_seconds=checker_wall,branches=branches)
            with (OUT/'runs.jsonl').open('a') as out:out.write(json.dumps(row)+'\n')
            print(name,mode,verdict,flush=True)
    (HERE/'terminal.json').write_text(json.dumps(dict(exit_code=0,rows=768,finished=time.time())))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','smoke','launch']);args=p.parse_args()
    if args.action=='prepare':prepare()
    else:
        plan=json.loads((HERE/'plan.json').read_text())
        (smoke if args.action=='smoke' else launch)(plan)
