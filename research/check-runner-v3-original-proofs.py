"""Check saved original-input positive and nested negative answers with the frozen v3 worker."""
import hashlib,json,shutil,sys
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];S=ROOT/'results/runner-smpt-single-core-v3/source/scripts';sys.path.insert(0,str(S))
from bounded_validation import run_validation
F=ROOT/'research/runner-smpt-single-core-v3/original-proofs';F.mkdir()
P=ROOT/'research/portfolio-reduced-v1';p=json.loads((P/'original-plan.json').read_text());rows=[]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
args=SimpleNamespace(native_python=sys.executable,validation_memory_mib=2048,validation_response_mib=64,validation_seconds=30,validation_dag_work=200000000)
for q in p['queries']:
 old=P/(q['name']+'.portfolio-reduced.original.json');log=F/old.name;shutil.copyfile(old,log)
 v=run_validation(q,ROOT/'benchmarks/general-development-v3',F,log,0,args,mode='rust-original-v1')
 expected='reachable' if q['name'].startswith('Refine') else 'unreachable'
 assert v['verdict']==expected,v
 rows.append(dict(query=q['name'],log_sha256=sha(log),validation=v));print(q['name'],v['verdict'],flush=True)
(F/'receipt.json').write_text(json.dumps(dict(status='passed',runner_manifest_sha256=sha(S.parent.parent/'files-sha256.json'),rows=rows),indent=2)+'\n')
