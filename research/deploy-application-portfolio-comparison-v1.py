import hashlib
from pathlib import Path
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[1]
HOST = 'jules@jules-b650-aorus-elite-ax-v2'
REMOTE = '/home/jules/experiments/pvass-publication'
PACKAGE = 'research/application-portfolio-comparison-v1-deploy.tar.gz'
EXPECTED = '50086d9f9a8e93ed7646137eb252428039892cbcdaaf600aea03713273ef4e99'
assert hashlib.sha256((ROOT / PACKAGE).read_bytes()).hexdigest() == EXPECTED
with (ROOT / PACKAGE).open('rb') as stream:
    subprocess.run(['tailscale', 'ssh', HOST, f'cat > {REMOTE}/{PACKAGE}'], stdin=stream, check=True)
code = f'''
import hashlib,json,tarfile
from pathlib import Path
from scripts.process_runner import workspace_workloads
assert not workspace_workloads(Path.cwd())
package=Path({PACKAGE!r})
assert hashlib.sha256(package.read_bytes()).hexdigest()=={EXPECTED!r}
with tarfile.open(package) as archive:
    assert len(archive.getmembers())==6
    for member in archive.getmembers():
        path=Path(member.name)
        assert member.isfile() and not path.is_absolute() and '..' not in path.parts
        assert path.parts[0] in ('research','benchmarks')
        if path.exists():assert path.read_bytes()==archive.extractfile(member).read()
    archive.extractall(Path.cwd(),filter='data')
plan_path=Path('research/application-portfolio-comparison-v1-plan.json')
assert hashlib.sha256(plan_path.read_bytes()).hexdigest()=='ee1d82106803fcd0b970b98757182c6959bb0a8a4371027d2484d30fcec4ee2e'
plan=json.loads(plan_path.read_text())
for name,expected in plan['required_file_sha256'].items():
    with Path(name).open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==expected,name
assert not Path(plan['output']).exists()
print(json.dumps(dict(deployed_members=6,registered_identities=len(plan['required_file_sha256']),expected_rows=plan['expected_rows'])),flush=True)
'''
subprocess.run(['tailscale', 'ssh', HOST,
                f'cd {REMOTE} && vendor/venv/bin/python -c ' + shlex.quote(code)], check=True)
