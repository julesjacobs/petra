"""Collect the complete Linux result directory after authoritative termination."""
import hashlib,json,shlex,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FOLDER='results/linux-application-walk-full-v1'
assert json.loads((ROOT/'research/application-walk-full-v1/terminal.json').read_text())['exit_code']==0
archive=ROOT/'research/application-walk-full-v1/results.tar.gz'
assert not archive.exists() and not (ROOT/FOLDER).exists()
code='''import sys,tarfile
from pathlib import Path
from scripts.process_runner import workspace_workloads
assert not workspace_workloads(Path.cwd())
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as archive:
 archive.add('results/linux-application-walk-full-v1',arcname='results/linux-application-walk-full-v1')
'''
command=['tailscale','ssh','jules@jules-b650-aorus-elite-ax-v2',"cd /home/jules/experiments/pvass-publication && vendor/venv/bin/python -c "+shlex.quote(code)]
with archive.open('xb') as output:subprocess.run(command,stdout=output,check=True)
with tarfile.open(archive) as source:
 for m in source.getmembers():
  p=Path(m.name)
  assert not p.is_absolute() and '..' not in p.parts and (m.isdir() or m.isfile())
  assert p==Path(FOLDER) or p.is_relative_to(FOLDER)
 source.extractall(ROOT,filter='data')
with archive.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
receipt=dict(status='collected',archive=str(archive.relative_to(ROOT)),sha256=digest,bytes=archive.stat().st_size,files=sum(p.is_file() for p in (ROOT/FOLDER).rglob('*')),rows=len((ROOT/FOLDER/'runs.jsonl').read_text().splitlines()),scope='Transfer complete; audit still required')
(ROOT/'research/application-walk-full-v1/collection.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
