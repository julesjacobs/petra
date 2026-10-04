"""Transfer fresh campaign artifacts, dispatch exact jobs, and collect terminal evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import tarfile
import tempfile
import shutil

F = Path(__file__).resolve().parent
ROOT = F.parents[1]
REL = str(F.relative_to(ROOT))
REMOTE = '/home/jules/experiments/pvass-publication'
HOST = 'jules@jules-b650-aorus-elite-ax-v2'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def ssh(code, **kwargs):
    return subprocess.run(['tailscale', 'ssh', HOST, 'cd ' + shlex.quote(REMOTE)
                           + ' && vendor/venv/bin/python -c ' + shlex.quote(code)], check=True, **kwargs)


def deploy_archive(path):
    path = path.resolve()
    code = '''import hashlib,json,sys,tarfile
from pathlib import Path
from scripts.process_runner import workspace_workloads
assert not workspace_workloads(Path.cwd()), 'Competing workspace workload'
files={}
with tarfile.open(fileobj=sys.stdin.buffer,mode='r|gz') as tar:
 for item in tar:
  p=Path(item.name)
  assert not p.is_absolute() and '..' not in p.parts and item.isfile()
  assert str(p).startswith(('research/competitive-linux-20261004/','benchmarks/'))
  data=tar.extractfile(item).read()
  if p.exists():assert p.read_bytes()==data, 'Refuse replacement: '+str(p)
  else:
   p.parent.mkdir(parents=True,exist_ok=True)
   with p.open('xb') as out:out.write(data)
   p.chmod(item.mode)
  files[str(p)]=hashlib.sha256(data).hexdigest()
print(json.dumps(dict(status='deployed',files=len(files))))
'''
    with path.open('rb') as source:
        result = ssh(code, stdin=source, capture_output=True, text=True)
    receipt = dict(archive=str(path.relative_to(ROOT)), archive_sha256=sha(path),
                   stdout=result.stdout, stderr=result.stderr)
    with path.with_suffix('.deployment.json').open('x') as out:
        json.dump(receipt, out, indent=2)
    print(json.dumps(receipt))


def inventory():
    pins = json.loads((F / 'input-sha256.json').read_text())
    code = '''import hashlib,json,sys
from pathlib import Path
pins=json.load(sys.stdin);result={}
for name,digest in pins.items():
 p=Path(name)
 result[name]='missing' if not p.exists() else ('matched' if hashlib.sha256(p.read_bytes()).hexdigest()==digest else 'mismatch')
print(json.dumps(result))
'''
    result = ssh(code, input=json.dumps(pins), text=True, capture_output=True)
    found = json.loads(result.stdout)
    with (F / 'input-inventory.json').open('x') as out:
        json.dump(found, out, indent=2)
    assert 'mismatch' not in found.values()
    with (F / 'input-deployment.tar.gz').open('xb') as stream, tarfile.open(fileobj=stream, mode='w|gz') as tar:
        for name, status in found.items():
            if status == 'missing':
                assert sha(ROOT / name) == pins[name]
                tar.add(ROOT / name, arcname=name, recursive=False)
    print(json.dumps({k: list(found.values()).count(k) for k in set(found.values())}))


def dispatch(kind):
    script = 'build.py' if kind == 'build' else 'run.py'
    suffix = 'build-dispatch' if kind == 'build' else 'dispatch'
    extra = [] if kind == 'build' else ['launch']
    expected = sha(F / script)
    code = f'''import hashlib,json,subprocess,psutil
from pathlib import Path
from scripts.process_runner import workspace_workloads
f=Path({REL!r});root=Path.cwd()
assert not workspace_workloads(root)
assert hashlib.sha256((f/{script!r}).read_bytes()).hexdigest()=={expected!r}
receipt=f/{(suffix+'.json')!r};assert not receipt.exists()
with (f/{(suffix+'.log')!r}).open('xb') as log:
 p=subprocess.Popen([str(root/'vendor/venv/bin/python'),str(root/f/{script!r}),*{extra!r}],cwd=root,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 d=dict(pid=p.pid,created=psutil.Process(p.pid).create_time(),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),script_sha256={expected!r})
 with receipt.open('x') as out:json.dump(d,out,indent=2)
print(json.dumps(d))
'''
    result = ssh(code, capture_output=True, text=True)
    d = json.loads(result.stdout)
    with (F / (suffix + '.json')).open('x') as out:
        json.dump(d, out, indent=2)
    print(json.dumps(d))


def poll(kind):
    suffix = 'build-dispatch' if kind == 'build' else 'dispatch'
    d = json.loads((F / (suffix + '.json')).read_text())
    terminal = 'build-receipt.json' if kind == 'build' else 'terminal.json'
    code = f'''import json,psutil
from pathlib import Path
f=Path({REL!r});d=json.loads((f/{(suffix+'.json')!r}).read_text());assert d=={d!r}
try:
 p=psutil.Process(d['pid']);live=p.create_time()==d['created'] and p.status()!=psutil.STATUS_ZOMBIE and Path('/proc/sys/kernel/random/boot_id').read_text().strip()==d['boot_id']
except psutil.NoSuchProcess:live=False
result=dict(live=live,terminal=json.loads((f/{terminal!r}).read_text()) if (f/{terminal!r}).exists() else None)
if {kind!r}=='campaign':
 result['blocks']=[dict(name=n,rows=sum(1 for _ in (Path('results/competitive-linux-20261004')/n/'runs.jsonl').open()) if (Path('results/competitive-linux-20261004')/n/'runs.jsonl').exists() else 0) for n in ['repeat1','repeat2']]
else:
 result['tail']=(f/'build-dispatch.log').read_text()[-2500:]
print(json.dumps(result))
'''
    print(ssh(code, text=True, capture_output=True).stdout)


def collect(kind):
    suffix = 'build-dispatch' if kind == 'build' else 'dispatch'
    d = json.loads((F / (suffix + '.json')).read_text())
    terminal = 'build-receipt.json' if kind == 'build' else 'terminal.json'
    names = ['build-receipt.json', 'build-receipt-v2.json', 'candidate-vass-reach', 'build.log', 'tests.log', 'tests-retry.log',
             'build-dispatch.json', 'build-dispatch.log'] if kind == 'build' else [
                 'execution.json', 'terminal.json', 'dispatch.json', 'dispatch.log',
                 'repeat1-execution.json', 'repeat1-terminal.json', 'repeat1.log',
                 'repeat2-execution.json', 'repeat2-terminal.json', 'repeat2.log']
    code = f'''import json,psutil,sys,tarfile
from pathlib import Path
f=Path({REL!r});d=json.loads((f/{(suffix+'.json')!r}).read_text());assert d=={d!r}
try:
 p=psutil.Process(d['pid']);live=p.create_time()==d['created'] and p.status()!=psutil.STATUS_ZOMBIE and Path('/proc/sys/kernel/random/boot_id').read_text().strip()==d['boot_id']
except psutil.NoSuchProcess:live=False
assert not live,'Registered job remains live'
assert (f/{terminal!r}).exists(),'Missing terminal evidence'
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as tar:
 for name in {names!r}:
  if (f/name).exists():tar.add(f/name,arcname=str(f/name),recursive=False)
 if {kind!r}=='campaign':tar.add('results/competitive-linux-20261004',recursive=True)
'''
    archive = F / (kind + '-evidence.tar.gz')
    with archive.open('xb') as stream:
        ssh(code, stdout=stream)
    with tempfile.TemporaryDirectory(prefix='pvass-competitive-collection-') as temp:
        staging = Path(temp)
        with tarfile.open(archive) as tar:
            for item in tar.getmembers():
                p = Path(item.name)
                assert not p.is_absolute() and '..' not in p.parts
                assert str(p).startswith((REL+'/', 'results/competitive-linux-20261004'))
                assert item.isfile() or item.isdir()
            tar.extractall(staging, filter='data')
        pins = {}
        for p in staging.rglob('*'):
            if not p.is_file():
                continue
            rel = p.relative_to(staging)
            pins[str(rel)] = sha(p)
            target = ROOT / rel
            if target.exists():
                assert sha(target) == sha(p), str(rel)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, target)
    receipt = dict(status='collected-not-audited', files_sha256=pins,
                   archive_sha256=sha(archive), bytes=archive.stat().st_size)
    with (F / (kind + '-collection.json')).open('x') as out:
        json.dump(receipt, out, indent=2)
    print(json.dumps(dict(status=receipt['status'], files=len(pins), bytes=receipt['bytes'])))


def fetch_qualification():
    names = ['plan.json', 'freeze-config.json', 'freeze.log', 'capability.json',
             'capability-plan.json', 'capability-harness.log', 'qualification.log',
             'components']
    code = f'''import sys,tarfile
from pathlib import Path
from scripts.process_runner import workspace_workloads
f=Path({REL!r})
assert not workspace_workloads(Path.cwd()), 'Competing workspace workload'
assert (f/'capability.json').exists(), 'Qualification not terminal'
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as tar:
 for name in {names!r}:
  if (f/name).exists():tar.add(f/name,arcname=str(f/name))
 tar.add('results/competitive-capability-20261004')
 tar.add('benchmarks/competitive-capability-20261004')
'''
    archive = F / 'qualification-evidence.tar.gz'
    with archive.open('xb') as stream:
        ssh(code, stdout=stream)
    pins = {}
    with tempfile.TemporaryDirectory(prefix='pvass-competitive-qualification-') as temp:
        staging = Path(temp)
        with tarfile.open(archive) as tar:
            for item in tar.getmembers():
                p = Path(item.name)
                assert not p.is_absolute() and '..' not in p.parts
                assert str(p).startswith((REL+'/', 'results/competitive-capability-20261004',
                                          'benchmarks/competitive-capability-20261004'))
                assert item.isfile() or item.isdir()
            tar.extractall(staging, filter='data')
        for p in staging.rglob('*'):
            if not p.is_file():
                continue
            rel = p.relative_to(staging)
            pins[str(rel)] = sha(p)
            target = ROOT / rel
            if target.exists():
                assert sha(target) == sha(p), str(rel)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, target)
    with (F / 'qualification-collection.json').open('x') as out:
        json.dump(dict(status='collected', files_sha256=pins, archive_sha256=sha(archive)), out, indent=2)
    print(json.dumps(dict(status='qualification-collected', files=len(pins))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['deploy', 'inventory', 'dispatch', 'poll', 'collect', 'fetch-qualification'])
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--kind', choices=['build', 'campaign'], default='campaign')
    args = parser.parse_args()
    if args.action == 'deploy':
        deploy_archive(args.archive)
    elif args.action == 'inventory':
        inventory()
    elif args.action == 'fetch-qualification':
        fetch_qualification()
    else:
        globals()[args.action](args.kind)
