"""Deploy missing registered evidence, rejecting divergent remote files."""
import hashlib
import io
import json
from pathlib import Path
import shlex
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
REMOTE = "/home/jules/experiments/pvass-publication"
HOST = "jules@jules-b650-aorus-elite-ax-v2"
PLAN = "research/application-walk-full-v1/plan.json"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def remote(code, **kwargs):
    return subprocess.run(["tailscale", "ssh", HOST,
                           f"cd {REMOTE} && vendor/venv/bin/python -c " + shlex.quote(code)],
                          check=True, **kwargs)


def main():
    plan = json.loads((ROOT / PLAN).read_text())
    pins = dict(plan["required_file_sha256"])
    pins[PLAN] = sha(ROOT / PLAN)
    inspect = '''
import hashlib,json,sys
from pathlib import Path
from scripts.process_runner import workspace_workloads
assert not workspace_workloads(Path.cwd())
pins=json.load(sys.stdin);missing=[]
for name,expected in pins.items():
    path=Path(name)
    assert not path.is_absolute() and '..' not in path.parts
    if not path.exists():missing.append(name);continue
    with path.open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==expected,name
print(json.dumps(missing))
'''
    missing = json.loads(remote(inspect, input=json.dumps(pins), text=True, capture_output=True).stdout)
    # Existing Linux tools are verified on Linux; same-named local tools may
    # target macOS. Only missing evidence is sourced from this workspace.
    assert all(sha(ROOT / name) == pins[name] for name in missing)
    package = ROOT / "research/application-walk-full-v1/deploy.tar.gz"
    assert not package.exists()
    with tarfile.open(package, "w:gz") as archive:
        for name in missing:
            archive.add(ROOT / name, arcname=name, recursive=False)
        data = json.dumps(pins).encode()
        info = tarfile.TarInfo("deployment-pins.json")
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))
    # The host was idle above, and extraction checks it again before writing.
    command = f"cat > {REMOTE}/research/application-walk-full-v1-deploy.tar.gz"
    with package.open("rb") as stream:
        subprocess.run(["tailscale", "ssh", HOST, command], stdin=stream, check=True)
    code = f'''
import hashlib,json,tarfile
from pathlib import Path
from scripts.process_runner import workspace_workloads
assert not workspace_workloads(Path.cwd())
package=Path('research/application-walk-full-v1-deploy.tar.gz')
with package.open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()=={sha(package)!r}
with tarfile.open(package) as archive:
    pins=json.load(archive.extractfile('deployment-pins.json'))
    members=[m for m in archive.getmembers() if m.name!='deployment-pins.json']
    assert len(members)=={len(missing)}
    for member in members:
        path=Path(member.name)
        assert member.isfile() and not path.is_absolute() and '..' not in path.parts
        data=archive.extractfile(member).read()
        assert hashlib.sha256(data).hexdigest()==pins[member.name]
        if path.exists():assert path.read_bytes()==data
        else:
            path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('xb') as stream:stream.write(data)
for name,expected in pins.items():
    with Path(name).open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==expected,name
assert not Path({plan['output']!r}).exists()
print(json.dumps(dict(deployed_members=len(members),registered_files=len(pins),plan_sha256=pins[{PLAN!r}])),flush=True)
'''
    remote(code)


if __name__ == "__main__":
    main()
