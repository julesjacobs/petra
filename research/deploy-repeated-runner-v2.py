"""Freeze and deploy a runtime dependency closure, preserving prior remote bytes."""
import ast
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
HOST = 'jules@jules-b650-aorus-elite-ax-v2'
REMOTE = '/home/jules/experiments/pvass-publication'
DEST = 'results/runner-repeated-search-v2'
out = ROOT / DEST
out.mkdir()
pending = ['benchmark_smpt_classic', 'benchmark', 'native_original', 'smpt_import',
           'bounded_validation', 'rust_original_validation', 'verifypn_runner',
           'linux_runner', 'process_runner']
seen = set()
while pending:
    name = pending.pop()
    source = ROOT / 'scripts' / (name + '.py')
    if name in seen or not source.exists():
        continue
    seen.add(name)
    for node in ast.walk(ast.parse(source.read_text())):
        if isinstance(node, ast.ImportFrom) and node.module:
            pending.append(node.module.split('.')[0])
        elif isinstance(node, ast.Import):
            pending.extend(alias.name.split('.')[0] for alias in node.names)
paths = [Path('scripts') / (name + '.py') for name in sorted(seen)] + [Path('scripts/requirements.txt')]
hashes = {str(path): hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}
(out / 'files-sha256.json').write_text(json.dumps(hashes, indent=2) + '\n')
with tarfile.open(out / 'runner.tar.gz', 'w:gz') as archive:
    for path in paths:
        archive.add(ROOT / path, arcname=str(path), recursive=False)


def remote(command, **kwargs):
    return subprocess.run(['tailscale', 'ssh', HOST, command], check=True, **kwargs)


remote(f'cd {REMOTE} && vendor/venv/bin/python -c ' + shlex.quote(
    'from pathlib import Path; from scripts.process_runner import workspace_workloads; '
    f'assert not workspace_workloads(Path.cwd()); Path({DEST!r}).mkdir()'))
for name in ('runner.tar.gz', 'files-sha256.json'):
    with (out / name).open('rb') as stream:
        remote(f'cat > {REMOTE}/{DEST}/{name}', stdin=stream)
code = f'''
import hashlib,json,tarfile
from pathlib import Path
dest=Path({DEST!r})
expected={hashes!r}
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
old={{name:sha(Path(name)) for name in expected if Path(name).exists()}}
with tarfile.open(dest/'runner.tar.gz') as archive:
    assert {{m.name for m in archive.getmembers()}}==set(expected)
    for member in archive.getmembers():
        assert member.isfile() and Path(member.name).parts[0]=='scripts'
        assert '..' not in Path(member.name).parts and not Path(member.name).is_absolute()
        assert hashlib.sha256(archive.extractfile(member).read()).hexdigest()==expected[member.name]
    with tarfile.open(dest/'previous-runner.tar.gz','w:gz') as backup:
        for name in old:backup.add(name,arcname=name,recursive=False)
    (dest/'previous-files-sha256.json').write_text(json.dumps(old,indent=2)+'\\n')
    archive.extractall(Path.cwd(),filter='data')
assert all(sha(Path(name))==value for name,value in expected.items())
print(json.dumps(dict(deployed=len(expected),preserved=len(old),files_sha256=expected),indent=2),flush=True)
'''
remote(f'cd {REMOTE} && vendor/venv/bin/python -c ' + shlex.quote(code))
