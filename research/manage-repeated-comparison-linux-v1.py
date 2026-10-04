"""Deploy, qualify, dispatch or observe the frozen repeated Linux comparison."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
F = ROOT/'research/repeated-comparison-linux-v1'
REL = str(F.relative_to(ROOT))
HOST = 'jules@jules-b650-aorus-elite-ax-v2'
REMOTE = '/home/jules/experiments/pvass-publication'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def ssh(code, **kwargs):
    return subprocess.run(['tailscale','ssh',HOST,'cd '+shlex.quote(REMOTE)+' && vendor/venv/bin/python -c '+shlex.quote(code)],check=True,**kwargs)

def deploy():
    sys.path.insert(0,str(ROOT/'scripts'))
    from process_runner import workspace_workloads
    assert not workspace_workloads(ROOT)
    suite=json.loads((F/'suite.json').read_text())
    pins=dict(suite['setup_sha256'])
    pins[REL+'/suite.json']=sha(F/'suite.json')
    pins['research/repeated-comparison-protocol-v1.md']=suite['protocol_sha256']
    for b in suite['blocks']:
        pins[REL+'/'+b['name']+'/plan.json']=b['plan_sha256']
    archive=F/'deployment.tar.gz'
    with archive.open('xb') as out,tarfile.open(fileobj=out,mode='w|gz') as tar:
        for path,digest in pins.items():
            assert sha(ROOT/path)==digest
            tar.add(ROOT/path,arcname=path,recursive=False)
    code=f'''import hashlib,json,sys,tarfile
from pathlib import Path
from scripts.process_runner import workspace_workloads
assert not workspace_workloads(Path.cwd())
parent=Path('research/portfolio-reduced-linux-v1')
assert json.loads((parent/'terminal.json').read_text())['exit_code']==0
f=Path({REL!r});assert not (f/'dispatch.json').exists()
with tarfile.open(fileobj=sys.stdin.buffer,mode='r|gz') as tar:
 for item in tar:
  p=Path(item.name);assert not p.is_absolute() and '..' not in p.parts and item.isfile()
  data=tar.extractfile(item).read()
  if p.exists():assert p.read_bytes()==data, 'Refuse replacement: '+str(p)
  else:
   p.parent.mkdir(parents=True,exist_ok=True)
   with p.open('xb') as out:out.write(data)
suite=json.loads((f/'suite.json').read_text())
plan=json.loads((f/suite['blocks'][0]['name']/'plan.json').read_text())
for name,digest in {{**plan['required_file_sha256'],**plan['preflight_file_sha256'],**{pins!r}}}.items():
 assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
print(json.dumps(dict(status='deployed-and-pinned',suite_sha256=hashlib.sha256((f/'suite.json').read_bytes()).hexdigest())))
'''
    with archive.open('rb') as source:
        result=ssh(code,stdin=source,capture_output=True,text=True)
    receipt=dict(status='passed',stdout=result.stdout,stderr=result.stderr,files=len(pins),archive_sha256=sha(archive))
    (F/'deployment.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))

def qualify():
    code="import subprocess; subprocess.run(['vendor/venv/bin/python','research/run-repeated-comparison-linux-v1.py','qualify'],check=True)"
    result=ssh(code,capture_output=True,text=True)
    (F/'qualification-run.log').write_text(result.stdout+result.stderr)
    print(result.stdout[-1000:])

def dispatch():
    assert not (F/'dispatch.json').exists()
    code=f'''import hashlib,json,subprocess,psutil
from pathlib import Path
from scripts.process_runner import workspace_workloads
root=Path.cwd();f=Path({REL!r});assert not workspace_workloads(root)
assert not any((f/name).exists() for name in ['dispatch.json','execution.json','terminal.json'])
suite_sha=hashlib.sha256((f/'suite.json').read_bytes()).hexdigest()
assert suite_sha=={sha(F/'suite.json')!r}
q=json.loads((f/'qualification.json').read_text());assert q['status']=='passed' and q['suite_sha256']==suite_sha
with (f/'run.log').open('xb') as log:
 p=subprocess.Popen([str(root/'vendor/venv/bin/python'),str(root/'research/run-repeated-comparison-linux-v1.py'),'launch'],cwd=root,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 d=dict(pid=p.pid,created=psutil.Process(p.pid).create_time(),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),suite_sha256=suite_sha)
 with (f/'dispatch.json').open('x') as out:json.dump(d,out,indent=2)
 print(json.dumps(d))
'''
    result=ssh(code,capture_output=True,text=True)
    d=json.loads(result.stdout)
    with (F/'dispatch.json').open('x') as out:json.dump(d,out,indent=2)
    print(json.dumps(d))

def poll():
    d=json.loads((F/'dispatch.json').read_text())
    code=f'''import json,psutil
from pathlib import Path
f=Path({REL!r});d=json.loads((f/'dispatch.json').read_text());assert d=={d!r}
try:
 p=psutil.Process(d['pid']);live=p.create_time()==d['created'] and p.status()!=psutil.STATUS_ZOMBIE and Path('/proc/sys/kernel/random/boot_id').read_text().strip()==d['boot_id']
except psutil.NoSuchProcess:live=False
suite=json.loads((f/'suite.json').read_text());blocks=[]
for b in suite['blocks']:
 folder=f/b['name'];plan=json.loads((folder/'plan.json').read_text());rows=Path(plan['output'])/'runs.jsonl'
 blocks.append(dict(name=b['name'],rows=sum(1 for _ in rows.open()) if rows.exists() else 0,terminal=json.loads((folder/'terminal.json').read_text()) if (folder/'terminal.json').exists() else None))
print(json.dumps(dict(pid=d['pid'],live=live,terminal=json.loads((f/'terminal.json').read_text()) if (f/'terminal.json').exists() else None,blocks=blocks)))
'''
    print(ssh(code,capture_output=True,text=True).stdout)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['deploy','qualify','dispatch','poll'])
    args=parser.parse_args()
    globals()[args.action]()
