"""Collect the repeated suite only after exact-job termination; preserve partial failures."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT=Path(__file__).resolve().parents[1]
F=Path('research/repeated-comparison-linux-v1')
OUT=Path('results/linux-repeated-comparison-v1')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--import-existing',action='store_true')
args=parser.parse_args()
sys.path.insert(0,str(ROOT/'scripts'))
from process_runner import workspace_workloads
assert not workspace_workloads(ROOT)
dispatch=json.loads((ROOT/F/'dispatch.json').read_text())
digest=sha(ROOT/F/'suite.json')
archive=ROOT/F/'results.tar.gz'
assert not (ROOT/F/'collection.json').exists()
if not args.import_existing:
    code=f'''import hashlib,json,psutil,sys,tarfile
from pathlib import Path
from scripts.process_runner import workspace_workloads
f=Path({str(F)!r});d=json.loads((f/'dispatch.json').read_text());assert d=={dispatch!r}
try:
 p=psutil.Process(d['pid']);live=p.create_time()==d['created'] and p.status()!=psutil.STATUS_ZOMBIE and Path('/proc/sys/kernel/random/boot_id').read_text().strip()==d['boot_id']
except psutil.NoSuchProcess:live=False
assert not live, 'Registered suite remains live'
t=json.loads((f/'terminal.json').read_text());assert t['suite_sha256']=={digest!r}
assert not workspace_workloads(Path.cwd()), 'Other remote workload'
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as tar:
 tar.add(str(f),arcname=str(f))
 output=Path({str(OUT)!r})
 if output.exists():tar.add(str(output),arcname=str(output))
'''
    with archive.open('xb') as stream:
        subprocess.run(['tailscale','ssh','jules@jules-b650-aorus-elite-ax-v2',
            'cd /home/jules/experiments/pvass-publication && vendor/venv/bin/python -c '+shlex.quote(code)],stdout=stream,check=True)
with tempfile.TemporaryDirectory(prefix='pvass-repeated-collection-') as temp:
    staging=Path(temp)
    with tarfile.open(archive) as tar:
        names=set()
        for item in tar.getmembers():
            p=Path(item.name)
            assert not p.is_absolute() and '..' not in p.parts
            assert p==F or p.is_relative_to(F) or p==OUT or p.is_relative_to(OUT)
            assert item.isfile() or item.isdir()
            assert item.name not in names
            names.add(item.name)
        tar.extractall(staging,filter='data')
    assert sha(staging/F/'suite.json')==digest
    assert json.loads((staging/F/'dispatch.json').read_text())==dispatch
    for name in ['execution.json','terminal.json']:
        assert json.loads((staging/F/name).read_text())['suite_sha256']==digest
    files=[p for p in staging.rglob('*') if p.is_file()]
    pins={str(p.relative_to(staging)):sha(p) for p in files}
    for p in files:
        dest=ROOT/p.relative_to(staging)
        if dest.exists():assert sha(dest)==sha(p),str(dest)
    for p in files:
        dest=ROOT/p.relative_to(staging)
        if not dest.exists():
            dest.parent.mkdir(parents=True,exist_ok=True)
            with p.open('rb') as source,dest.open('xb') as target:shutil.copyfileobj(source,target)
receipt=dict(status='collected-not-audited',suite_sha256=digest,files_sha256=pins,
             archive_sha256=sha(archive),bytes=archive.stat().st_size)
(ROOT/F/'collection.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(dict(status=receipt['status'],files=len(pins),bytes=receipt['bytes'])))
