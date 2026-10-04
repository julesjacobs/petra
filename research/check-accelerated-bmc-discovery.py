"""Controlled encoding ablation for an automatically discovered control cycle."""
from pathlib import Path
import json,subprocess,tempfile,importlib.util,hashlib
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('base',ROOT/'research/check-accelerated-bmc-prototype.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
p=dict(places=['a','b','count'],initial=[1,0,0],transitions=[dict(name='a_to_b',pre=[[0,1]],post=[[1,1],[2,1]]),dict(name='b_to_a',pre=[[1,1]],post=[[0,1]])],target=[dict(coefficients=[0,0,1],bound=10**12,equality=True),dict(coefficients=[1,0,0],bound=1,equality=True)])
rows=[]
with tempfile.TemporaryDirectory(prefix='pvass-discovery-') as tmp:
 d=Path(tmp); (d/'p.json').write_text(json.dumps(p))
 command=[str(base.EXAMPLE),'discover',str(d/'p.json'),'8','16','10000']
 discovery=json.loads(subprocess.check_output(command,text=True,timeout=10))
 assert discovery['words']==[[0],[1],[0,1],[1,0]] and not discovery['truncated']
 for name,mode,words,expected in [('ordinary','emit-bmc',[[0],[1]],'unsat'),('singleton-acceleration','emit',[[0],[1]],'unsat'),('discovered-word-acceleration','emit',discovery['words'],'sat')]:
  (d/'words.json').write_text(json.dumps(words))
  cmd=[str(base.EXAMPLE),mode,str(d/'p.json'),str(d/'words.json'),'2']
  formula=subprocess.check_output(cmd,text=True,timeout=10)
  result=subprocess.run([str(base.Z3),'-in','-T:5'],input=formula,text=True,capture_output=True,timeout=10)
  status=result.stdout.splitlines()[0]; assert status==expected,(name,result.stdout)
  (d/'model').write_text(result.stdout);cmd[1]='check';cmd.append(str(d/'model'))
  answer=json.loads(subprocess.check_output(cmd,text=True,timeout=10))
  if status=='sat':assert base.check_compressed(p,answer['segments'])==[1,0,10**12]
  else:assert answer['verdict']=='unknown'
  rows.append(dict(method=name,depth=2,status=status,answer=answer,formula_sha256=hashlib.sha256(formula.encode()).hexdigest()))
record=dict(status='passed',scope='Synthetic mechanism ablation; no competitive performance evidence',discovery=discovery,rows=rows)
(ROOT/'research/accelerated-bmc-discovery-check.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
