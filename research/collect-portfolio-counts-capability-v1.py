from pathlib import Path
import subprocess,shlex,tarfile,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'research/portfolio-counts-linux-v1'
paths=['benchmarks/portfolio-counts-capability-v1','results/linux-portfolio-counts-capability-v1']
paths += ['research/portfolio-counts-linux-v1/'+x for x in ['capability.json','capability-harness.json','capability-v3-plan.json','capability-v3-terminal.json','components']]
code='import tarfile,sys\nfrom pathlib import Path\nfrom scripts.process_runner import workspace_workloads\nassert not workspace_workloads(Path.cwd())\nwith tarfile.open(fileobj=sys.stdout.buffer,mode="w|gz") as tar:\n for p in '+repr(paths)+':tar.add(p,arcname=p)\n'
archive=FOLDER/'capability-evidence.tar.gz'
with archive.open('xb') as out:
 subprocess.run(['tailscale','ssh','jules@jules-b650-aorus-elite-ax-v2','cd /home/jules/experiments/pvass-publication && vendor/venv/bin/python -c '+shlex.quote(code)],stdout=out,check=True)
with tarfile.open(archive) as tar:
 for m in tar:
  p=Path(m.name); assert not p.is_absolute() and '..' not in p.parts and (m.isdir() or m.isfile())
  target=ROOT/p
  if m.isdir():target.mkdir(parents=True,exist_ok=True);continue
  data=tar.extractfile(m).read(); target.parent.mkdir(parents=True,exist_ok=True)
  if target.exists():assert target.read_bytes()==data,str(p)
  else:
   with target.open('xb') as out:out.write(data)
print(json.dumps(dict(bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest())))
