"""Preserve and deploy the already-tested candidate source for a fresh Linux build."""
import hashlib,json,shlex,shutil,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'research/portfolio-reduced-linux-v1';DEST=ROOT/'results/linux-solver-portfolio-reduced-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((ROOT/'research/portfolio-reduced-development-v1/plan.json').read_text())
assert not DEST.exists();(DEST/'source').mkdir(parents=True)
for name,digest in plan['source_sha256'].items():
 p=ROOT/'results/solver-portfolio-reduced-development-v1/source'/name;assert sha(p)==digest
 dest=DEST/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
(DEST/'source-files-sha256.json').write_text(json.dumps(plan['source_sha256'],indent=2)+'\n')
archive=F/'candidate-source.tar.gz'
with tarfile.open(archive,'x:gz') as tar:
 tar.add(DEST,arcname=str(DEST.relative_to(ROOT)))
 tar.add(ROOT/'research/build-portfolio-reduced-linux-v1.py',arcname='research/build-portfolio-reduced-linux-v1.py')
code='''import sys,tarfile
from pathlib import Path
from scripts.process_runner import workspace_workloads
assert not workspace_workloads(Path.cwd())
with tarfile.open(fileobj=sys.stdin.buffer,mode='r|gz') as tar:
 for m in tar:
  p=Path(m.name);assert not p.is_absolute() and '..' not in p.parts
  if m.isdir():p.mkdir(parents=True,exist_ok=True);continue
  assert m.isfile();data=tar.extractfile(m).read()
  if p.exists():assert p.read_bytes()==data,str(p)
  else:
   p.parent.mkdir(parents=True,exist_ok=True)
   with p.open('xb') as f:f.write(data)
print('candidate source deployed')
'''
with archive.open('rb') as stream:
 r=subprocess.run(['tailscale','ssh','jules@jules-b650-aorus-elite-ax-v2','cd /home/jules/experiments/pvass-publication && vendor/venv/bin/python -c '+shlex.quote(code)],stdin=stream,capture_output=True,text=True)
(F/'source-deployment.json').write_text(json.dumps(dict(exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr,archive_sha256=sha(archive)),indent=2)+'\n')
print(r.stdout,r.stderr);r.check_returncode()
