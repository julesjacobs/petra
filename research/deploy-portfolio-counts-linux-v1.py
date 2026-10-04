"""Deploy missing frozen files; reject replacement of different remote bytes."""
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'research/portfolio-counts-linux-v1'
REMOTE = '/home/jules/experiments/pvass-publication'
HOST = 'jules@jules-b650-aorus-elite-ax-v2'


def main():
    plan = json.loads((FOLDER / 'plan.json').read_text())
    inventory = json.loads((FOLDER / 'deployment-inventory.json').read_text())
    pins = {**plan['required_file_sha256'], **plan['preflight_file_sha256']}
    pins['research/portfolio-counts-linux-v1/plan.json'] = hashlib.sha256((FOLDER / 'plan.json').read_bytes()).hexdigest()
    alias = plan['runner_vendor_symlink']['path']
    selected = []
    for name, record in inventory.items():
        if record['status'] == 'mismatch':
            raise RuntimeError('Remote mismatch: ' + name)
        if record['status'] != 'missing' or name.startswith(alias + '/'):
            continue
        with (ROOT / name).open('rb') as stream:
            assert hashlib.file_digest(stream, 'sha256').hexdigest() == pins[name], name
        selected.append(name)
    archive = FOLDER / 'deployment.tar.gz'
    with archive.open('xb') as stream, tarfile.open(fileobj=stream, mode='w|gz') as tar:
        for name in selected:
            tar.add(ROOT / name, arcname=name, recursive=False)
    code = '''import hashlib,json,sys,tarfile
from pathlib import Path
from scripts.process_runner import workspace_workloads
assert not workspace_workloads(Path.cwd()), 'Competing workload'
with tarfile.open(fileobj=sys.stdin.buffer,mode='r|gz') as tar:
 for member in tar:
  p=Path(member.name)
  assert not p.is_absolute() and '..' not in p.parts and member.isfile()
  data=tar.extractfile(member).read()
  if p.exists():assert p.read_bytes()==data, 'Refuse replacement: '+str(p)
  else:
   p.parent.mkdir(parents=True,exist_ok=True)
   with p.open('xb') as out:out.write(data)
plan=json.loads(Path('research/portfolio-counts-linux-v1/plan.json').read_text())
link=Path(plan['runner_vendor_symlink']['path'])
if not link.is_symlink():link.symlink_to(plan['runner_vendor_symlink']['target'])
assert link.resolve()==Path('vendor').resolve()
for name,expected in {**plan['required_file_sha256'],**plan['preflight_file_sha256']}.items():
 with Path(name).open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==expected,name
print(json.dumps({'status':'deployed-all-pins-verified','runtime_pins':len(plan['required_file_sha256']),'preflight_pins':len(plan['preflight_file_sha256'])}))
'''
    with archive.open('rb') as source:
        result = subprocess.run(['tailscale', 'ssh', HOST, 'cd ' + REMOTE + ' && vendor/venv/bin/python -c ' + shlex.quote(code)], stdin=source, text=True, capture_output=True)
    receipt = dict(exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr, files=len(selected), archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    (FOLDER / 'deployment.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))
    result.check_returncode()


if __name__ == '__main__':
    main()
