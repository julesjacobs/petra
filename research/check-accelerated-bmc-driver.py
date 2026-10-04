"""Exercise whole-query driver verdicts, discovery, and independent checking."""
from pathlib import Path
import importlib.util,json,subprocess,sys,tempfile,hashlib
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('check',ROOT/'scripts/check_accelerated_witness.py');check=importlib.util.module_from_spec(spec);spec.loader.exec_module(check)
p=dict(places=['a','b','count'],initial=[1,0,0],transitions=[dict(name='ab',pre=[[0,1]],post=[[1,1],[2,1]]),dict(name='ba',pre=[[1,1]],post=[[0,1]])],target=[dict(coefficients=[0,0,1],bound=10**12,equality=True),dict(coefficients=[1,0,0],bound=1,equality=True)])
rows=[]
with tempfile.TemporaryDirectory(prefix='pvass-abmc-driver-') as tmp:
 problem=Path(tmp)/'problem.json';problem.write_text(json.dumps(p))
 base=[sys.executable,str(ROOT/'scripts/accelerated_bmc.py'),'--problem',str(problem),'--depth-limit','2','--seconds','5']
 for mode in ['ordinary','singleton','cycles']:
  result=json.loads(subprocess.check_output(base+['--mode',mode],text=True,timeout=10))
  assert result['verdict']==('reachable' if mode=='cycles' else 'unknown'),result
  if mode=='cycles':assert check.check(p,result['segments'])==[1,0,10**12]
  rows.append(result)
 result=json.loads(subprocess.check_output(base+['--seconds','0.000000001'],text=True,timeout=10));assert result['verdict']=='unknown' and 'deadline' in result['reason'];rows.append(result)
 result=json.loads(subprocess.check_output(base+['--z3','/usr/bin/false'],text=True,timeout=10));assert result['verdict']=='unknown' and result['reason']=='SMT failure';rows.append(result)
 p=dict(places=['x'],initial=[0],transitions=[],target=[dict(coefficients=[1],bound=0,equality=True)])
 problem.write_text(json.dumps(p));result=json.loads(subprocess.check_output(base,text=True,timeout=10));assert result['verdict']=='reachable';check.check(p,result['segments']);rows.append(result)
record=dict(status='passed',runs=len(rows),rows=rows,source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'src/accelerated_bmc.rs',ROOT/'src/word_discovery.rs',ROOT/'examples/accelerated_bmc.rs',ROOT/'scripts/accelerated_bmc.py',Path(__file__)]})
(ROOT/'research/accelerated-bmc-driver-check.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(dict(status='passed',runs=len(rows))))
