"""Native automatic-search end-to-end mechanism and independent witness checks."""
import importlib.util, json, subprocess, tempfile, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('checker',ROOT/'scripts/check_accelerated_witness.py')
checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
p=dict(places=['a','b','count'],initial=[1,0,0],transitions=[
    dict(name='ab',pre=[[0,1]],post=[[1,1],[2,1]]),dict(name='ba',pre=[[1,1]],post=[[0,1]])],
    target=[dict(coefficients=[0,0,1],bound=10**12,equality=True),dict(coefficients=[1,0,0],bound=1,equality=True)])
rows=[]
with tempfile.TemporaryDirectory(prefix='pvass-native-search-') as tmp:
 path=Path(tmp)/'p.json'
 for label,problem,mode,expected in [
     ('accelerated-control',p,'cycles','reachable'),
     ('bounded-singletons',p,'singleton','unknown'),
     ('disabled-control',dict(p,initial=[0,0,0]),'cycles','unknown'),
     ('initial',dict(p,target=[]),'cycles','reachable')]:
  path.write_text(json.dumps(problem))
  result=json.loads(subprocess.check_output([str(ROOT/'target/release/examples/native_scheme_search'),str(path),'3',mode],text=True,timeout=5))
  assert result['verdict']==expected,(label,result)
  if expected=='reachable':
   assert list(map(int,result['marking']))==checker.check(problem,result['segments'])
   answer_path=Path(tmp)/'answer.json';answer_path.write_text(json.dumps(result))
   subprocess.run([__import__('sys').executable,str(ROOT/'scripts/check_accelerated_witness.py'),str(path),str(answer_path)],check=True,capture_output=True,text=True,timeout=5)
  rows.append(dict(label=label,answer=result))
f=ROOT/'research/native-scheme-root-guards-v1'
record=dict(status='passed',rows=rows,source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'src/scheme_search.rs',ROOT/'src/path_scheme.rs',ROOT/'examples/native_scheme_search.rs',Path(__file__)]},binary_sha256=hashlib.sha256((ROOT/'target/release/examples/native_scheme_search').read_bytes()).hexdigest())
(f/'semantic.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(dict(status='passed',cases=len(rows))))
