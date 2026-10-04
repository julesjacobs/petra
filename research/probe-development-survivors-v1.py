"""Budget scaling on every unresolved property from the completed combined development screen."""
import hashlib,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from process_runner import run,workspace_workloads
F=ROOT/'research/development-survivors-v1';C=ROOT/'benchmarks/mcc2021-development'
S=ROOT/'results/solver-portfolio-reduced-development-v1'
MODES={'combined':('candidate','portfolio-reduced'),'counts':('native-counts','portfolio-walk-counts')}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not workspace_workloads(ROOT);F.mkdir()
a=ROOT/'research/portfolio-reduced-development-v1/audit.json';assert json.loads(a.read_text())['status']=='passed'
prior=ROOT/'results/portfolio-reduced-development-v1/runs.jsonl'
rows=[json.loads(x) for x in prior.read_text().splitlines()]
names=sorted(r['query'] for r in rows if r['mode']=='candidate' and r['verdict']=='unknown');assert len(names)==3
queries={q['name']:q for q in json.loads((C/'manifest.json').read_text())['queries']}
plan=dict(scope=__doc__,properties=names,modes=MODES,budgets=[1,5,20],rows=18,max_states=2000000,sampled_memory_bytes=2**31,checker_seconds=30,selection_sha256={str(p.relative_to(ROOT)):sha(p) for p in [a,prior]},binary_sha256={m:sha(S/b) for m,(b,_) in MODES.items()},source_plan_sha256=sha(ROOT/'research/portfolio-reduced-development-v1/plan.json'),script_sha256=sha(Path(__file__)),input_sha256={str((C/b['path']).resolve().relative_to(ROOT)):sha(C/b['path']) for n in names for b in queries[n]['branches']})
(F/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
for seconds in plan['budgets']:
 for qi,name in enumerate(names):
  q=queries[name]
  for mode in list(MODES)[qi%2:]+list(MODES)[:qi%2]:
   started=time.monotonic();checker_wall=0.;branches=[];verdict='unknown'
   for bi,b in enumerate(q['branches']):
    remaining=seconds-(time.monotonic()-started-checker_wall)
    if remaining<=0:break
    share=remaining/(len(q['branches'])-bi);problem=C/b['path'];prefix=F/f'{name}.{seconds}.{mode}.{bi}';log=Path(str(prefix)+'.json')
    binary,engine=MODES[mode];cmd=[str(S/binary),'--json',str(problem),'--method',engine,'--seconds',str(share),'--max-states','2000000']
    wall,code,expired,res=run(cmd,ROOT,share,log,2**31)
    try:answer=json.loads(log.read_text())
    except ValueError:answer={}
    br=dict(branch=bi,command=cmd,wall=wall,exit_code=code,expired=expired,resources=res,log_sha256=sha(log),candidate_verdict=answer.get('verdict'),reason=answer.get('reason'),states=answer.get('states'),verdict='unknown');branches.append(br)
    if code==0 and not expired and wall<=share and time.monotonic()-started-checker_wall<=seconds and not res['memory_limit_exceeded'] and answer.get('verdict') in ['reachable','unreachable']:
     check=Path(str(prefix)+'.check.json');cw,cc,ce,cr=run([sys.executable,str(S/'source/scripts/check_backend_answer.py'),str(problem),str(log)],ROOT,30,check,2**31)
     checker_wall+=cw;br['check']=dict(wall=cw,exit_code=cc,expired=ce,resources=cr,log_sha256=sha(check))
     assert cc==0 and not ce and not cr['memory_limit_exceeded'],br
     assert json.loads(check.read_text())['status']=='passed'
     br['verdict']=answer['verdict']
    if br['verdict']=='reachable':verdict='reachable';break
   if verdict!='reachable' and len(branches)==len(q['branches']) and all(b['verdict']=='unreachable' for b in branches):verdict='unreachable'
   row=dict(query=name,mode=mode,seconds=seconds,verdict=verdict,solver_wall_seconds=time.monotonic()-started-checker_wall,checker_wall_seconds=checker_wall,branches=branches)
   with (F/'runs.jsonl').open('a') as out:out.write(json.dumps(row)+'\n')
   print(name,seconds,mode,verdict,flush=True)
(F/'terminal.json').write_text(json.dumps(dict(exit_code=0,rows=18))+'\n')
