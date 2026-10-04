import argparse,sys,json,hashlib,shutil,os
from pathlib import Path
from datetime import datetime,timezone
import psutil
root=Path(__file__).resolve().parents[2]; here=Path(__file__).resolve().parent
out=root/'results/verifypn-learning-20261004/remaining-lp-diagnostic';out.mkdir(parents=True)
snapshot=here/'remaining-lp-diagnostic-snapshot';snapshot.mkdir()
shutil.copytree(root/'scripts',snapshot/'scripts',ignore=shutil.ignore_patterns('__pycache__'))
shutil.copy2(__file__,snapshot/'remaining-lp-diagnostic.py')
sys.path.insert(0,str(snapshot/'scripts'))
import benchmark_smpt_classic as runner
runner.ROOT=root
from bounded_validation import InputChecks
checks=InputChecks();corpus=root/'benchmarks/competitive-development-v5';manifest=corpus/'manifest.json'
qs=[q for q in json.loads(manifest.read_text())['queries'] if q['name'] in ['ASLink-PT-05b__RC06','ASLink-PT-10b__RC05','ASLink-PT-10b__RC07','RERS17pb114-PT-5__RC12']]
binary=here/'baseline/vass-reach'
pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [binary,manifest,*[p for p in snapshot.rglob('*') if p.is_file()]]}
for q in qs:
 for k in ['pnml','xml','net','property']:pins[str(corpus/q[k])]=q[k+'_sha256']
 for b in q['branches']:pins[str(corpus/b['path'])]=b['sha256']
for p,h in pins.items():checks.check(Path(p),h)
methods=['sparse-state-equation']
a=argparse.Namespace(seconds=5.,max_states=2000000,outer_grace=0.,memory_mib=2048,track_resources=True,linux_cpus=None,perf=False,native_tools={m:dict(binary=str(binary),engine=m) for m in methods},buffer_agglomeration_method=[],target_zero_trap_method=[],target_path_potential_method=[],geometric_branches_method=[],native_python=Path(sys.executable),validation_seconds=60.,validation_memory_mib=2048,validation_response_mib=64,validation_dag_work=200000000,bounded_validation=True)
(here/'remaining-lp-diagnostic-plan.json').write_text(json.dumps(dict(pins=pins,queries=[q['name'] for q in qs],methods=methods,seconds=5,scope='Contended selected diagnostic; no coverage or speed claim',utc=datetime.now(timezone.utc).isoformat()),indent=2))
with (out/'runs.jsonl').open('x') as f:
 for q in qs:
  for m in methods:
   checks.unchanged();host=dict(load=os.getloadavg(),cpu_percent=psutil.cpu_percent(interval=.2))
   r=runner.rust_original(q,corpus,out,m,0,a);r.update(query=q['name'],method=m,host=host)
   f.write(json.dumps(r)+'\n');f.flush();print(q['name'],m,r['verdict'],round(r['wall_seconds'],3),r.get('independent_checks'),flush=True)
checks.unchanged()
