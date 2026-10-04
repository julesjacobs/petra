"""Frozen full-classical-cohort mechanism screen; not a competitive solver comparison."""
from pathlib import Path
import hashlib,json,random,shutil,sys,time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from process_runner import run,workspace_workloads
CORPUS=ROOT/'benchmarks/smpt-classic'
OUT=ROOT/'results/abmc-classic-mechanism-v1'
FROZEN=ROOT/'results/solver-accelerated-bmc-v1'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    assert not workspace_workloads(ROOT)
    assert not OUT.exists() and not FROZEN.exists()
    queries=json.loads((CORPUS/'manifest.json').read_text())['queries'];assert len(queries)==37
    inputs={'benchmarks/smpt-classic/manifest.json':sha(CORPUS/'manifest.json')}
    for q in queries:
        assert q['status']=='imported'
        for b in q['branches']:
            p=CORPUS/b['path'];assert sha(p)==b['sha256'];inputs[str(p.relative_to(ROOT))]=b['sha256']
    FROZEN.mkdir();OUT.mkdir()
    paths=list((ROOT/'src').glob('*.rs'))+[ROOT/'Cargo.toml',ROOT/'Cargo.lock',ROOT/'examples/accelerated_bmc.rs',ROOT/'scripts/accelerated_bmc.py',ROOT/'scripts/check_accelerated_witness.py',ROOT/'scripts/process_runner.py',Path(__file__)]
    paths += [p for p in (ROOT/'vendor/varisat').rglob('*') if p.is_file() and '.git' not in p.parts and 'target' not in p.parts]
    pins={}
    for p in paths:
        dest=FROZEN/'source'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest);pins[str(p.relative_to(ROOT))]=sha(p)
    binary=FROZEN/'accelerated_bmc';shutil.copy2(ROOT/'target/release/examples/accelerated_bmc',binary)
    modes=['ordinary','singleton','cycles'];seconds=1.;random.Random(2026092804).shuffle(queries)
    plan=dict(properties=37,rows=111,seconds=seconds,modes=modes,repeat=1,depth_limit=16,word_length=8,extra_words=128,discovery_work=2000000,encoding_cells=200000,formula_bytes=67108864,sampled_memory_bytes=2**31,order_seed=2026092804,query_order=[q['name'] for q in queries],input_sha256=inputs,source_sha256=pins,binary_sha256=sha(binary),z3_sha256=sha(ROOT/'vendor/venv/bin/z3'),python=sys.executable,scope='Full 37-slot classical development cohort, canonical-input positive witness screen. All three configurations use identical Rust/Z3 implementations except acceleration/vocabulary. No native/SMPT competitor comparison; no stable speed inference. Separate bounded independent checking.')
    (OUT/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    for qi,q in enumerate(queries):
        for mode in modes[qi%3:]+modes[:qi%3]:
            started=time.monotonic();branches=[];verdict='unknown';checker_wall=0.0
            for bi,b in enumerate(q['branches']):
                remaining=seconds-(time.monotonic()-started)
                if remaining<=0:break
                share=remaining/(len(q['branches'])-bi)
                prefix=f"{q['name']}.{mode}.{bi}"
                problem=CORPUS/b['path'];log=OUT/(prefix+'.json')
                command=[sys.executable,str(FROZEN/'source/scripts/accelerated_bmc.py'),'--problem',str(problem),'--binary',str(binary),'--z3',str(ROOT/'vendor/venv/bin/z3'),'--mode',mode,'--seconds',str(share),'--artifacts',str(OUT/(prefix+'.artifacts'))]
                wall,code,expired,resources=run(command,ROOT,share,log,2**31)
                branch=dict(branch=bi,wall_seconds=wall,exit_code=code,expired=expired,resources=resources,command=command)
                try:answer=json.loads(log.read_text())
                except (ValueError,OSError):answer={}
                branch['verdict']=answer.get('verdict','unknown');branch['reason']=answer.get('reason')
                branches.append(branch)
                if answer.get('verdict')=='reachable' and code==0 and not expired and wall<=share and not resources['memory_limit_exceeded']:
                    solver_wall=time.monotonic()-started
                    if solver_wall>seconds:
                        branch['late_answer']=True
                        break
                    verify=[sys.executable,str(FROZEN/'source/scripts/check_accelerated_witness.py'),str(problem),str(log)]
                    validation=OUT/(prefix+'.validation.json')
                    vwall,vcode,vexpired,vres=run(verify,ROOT,30,validation,2**31)
                    checker_wall+=vwall
                    branch['validation']=dict(wall_seconds=vwall,exit_code=vcode,expired=vexpired,resources=vres,command=verify)
                    if vcode==0 and not vexpired and json.loads(validation.read_text())['status']=='passed':verdict='reachable'
                    break
            solver_wall=time.monotonic()-started-checker_wall
            row=dict(query=q['name'],kind=q['kind'],mode=mode,verdict=verdict,property_truth=(q['kind']=='EF') if verdict=='reachable' else None,solver_wall_seconds=solver_wall,branches=branches)
            with (OUT/'runs.jsonl').open('a') as stream:stream.write(json.dumps(row)+'\n')
            print(q['name'],mode,verdict,flush=True)
    (OUT/'terminal.json').write_text(json.dumps(dict(exit_code=0,rows=111)))

if __name__=='__main__':main()
