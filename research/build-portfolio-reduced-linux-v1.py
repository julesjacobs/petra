"""Build the preserved candidate sources on Linux, without touching frozen controls."""
import hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
F=ROOT/'results/linux-solver-portfolio-reduced-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sys.platform=='linux' and str(ROOT)=='/home/jules/experiments/pvass-publication'
sys.path.insert(0,str(ROOT/'scripts'))
from process_runner import workspace_workloads
assert not workspace_workloads(ROOT)
pins=json.loads((F/'source-files-sha256.json').read_text())
for name,digest in pins.items():assert sha(F/'source'/name)==digest,name
assert not (F/'build-receipt.json').exists() and not (F/'vass-reach').exists()
env=dict(os.environ,PATH=str(Path.home()/'.cargo/bin')+':'+os.environ['PATH'])
link=F/'source/vendor/venv'
assert not link.exists() and not link.is_symlink()
link.symlink_to(ROOT/'vendor/venv',target_is_directory=True)
start=time.time()
with (F/'build.log').open('x') as log:
 r=subprocess.run(['cargo','+1.97.1','build','--locked','--offline','--release','--bin','vass-reach'],cwd=F/'source',env=env,stdout=log,stderr=subprocess.STDOUT)
receipt=dict(test_python_sha256=sha(ROOT/'vendor/venv/bin/python'),test_python_link=str(link.resolve()),exit_code=r.returncode,started=start,finished=time.time(),source_manifest_sha256=sha(F/'source-files-sha256.json'),build_log_sha256=sha(F/'build.log'),script_sha256=sha(Path(__file__)),rustc=subprocess.check_output(['rustc','+1.97.1','-Vv'],env=env,text=True),cargo=subprocess.check_output(['cargo','+1.97.1','-V'],env=env,text=True))
if r.returncode==0:
 with (F/'tests.log').open('x') as log:
  tested=subprocess.run(['cargo','+1.97.1','test','--locked','--offline','--release','--test','reduced_bfs','--test','count_cap'],cwd=F/'source',env=env,stdout=log,stderr=subprocess.STDOUT)
 receipt['tests_exit_code']=tested.returncode;receipt['tests_log_sha256']=sha(F/'tests.log')
 shutil.copy2(F/'source/target/release/vass-reach',F/'vass-reach');receipt['binary_sha256']=sha(F/'vass-reach')
(F/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt));raise SystemExit(r.returncode or receipt.get('tests_exit_code',0))
