"""Independently translate original input, reconstruct reductions and exhaust reduced closure."""
import json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from native_original import translate
from buffer_agglomeration_checker import reconstruct
from relevance_checker import project
from benchmark import verify
C=ROOT/'benchmarks/general-development-v3'
q=next(q for q in json.loads((C/'manifest.json').read_text())['queries'] if q['name']=='CloudReconfiguration-PT-311__RC06')
branch=int(sys.argv[1]);answer=json.loads(Path(sys.argv[2]).read_text())
net,prop=translate(C/q['pnml'],C/q['xml'],q['property_id'])
for t in net['transitions']:
 for field in ['pre','post']:t[field]=[list(a) for a in t[field]]
assert len(prop['targets'])==len(q['branches'])==2 and prop['kind']==q['kind']
for i,b in enumerate(q['branches']):assert json.loads((C/b['path']).read_text())==dict(net,target=prop['targets'][i])
p=dict(net,target=prop['targets'][branch]);deadline=time.monotonic()+30
for step in answer['reductions']:
 if step['kind']=='buffer':
  assert set(step)=={'kind','steps'};p=reconstruct(p,step['steps'],deadline=deadline)
 elif step['kind']=='relevance':
  assert set(step)=={'kind','places','transitions'};p=project(p,step['places'],step['transitions'],deadline=deadline)
 else:raise ValueError('unknown reduction')
assert p==answer['reduced_problem']
assert answer['answer']['verdict']=='unreachable'
check=verify(p,answer['answer']);assert check=='python-finite-closure'
print(json.dumps(dict(status='passed',branch=branch,check='original-input-reduction-chain-and-finite-closure',leaf_check=check,places=len(p['places']),transitions=len(p['transitions']))))
