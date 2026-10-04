"""Deploy the frozen source to a new directory and build without changing old tools."""
import hashlib
import json
from pathlib import Path
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[1]
HOST = 'jules@jules-b650-aorus-elite-ax-v2'
REMOTE = '/home/jules/experiments/pvass-publication'
DEST = 'results/linux-solver-walk-sparse-v1'
SOURCE = ROOT / 'results/solver-walk-sparse-v1/source.tar.gz'
HASHES = ROOT / 'results/solver-walk-sparse-v1/source-files-sha256.json'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def remote(command, **kwargs):
    return subprocess.run(['tailscale', 'ssh', HOST, command], check=True, **kwargs)


remote(f'cd {REMOTE} && vendor/venv/bin/python -c ' + shlex.quote(
    'from pathlib import Path; from scripts.process_runner import workspace_workloads; '
    'assert not workspace_workloads(Path.cwd()); '
    f'Path({DEST!r}).mkdir()'))
for source, name in [(SOURCE, 'source.tar.gz'), (HASHES, 'source-files-sha256.json')]:
    with source.open('rb') as stream:
        remote(f'cat > {REMOTE}/{DEST}/{name}', stdin=stream)
code = f'''
import hashlib,json,subprocess,tarfile
from pathlib import Path
dest=Path({DEST!r})
archive=dest/'source.tar.gz'
with archive.open('rb') as stream:
    assert hashlib.file_digest(stream,'sha256').hexdigest()=={digest(SOURCE)!r}
hashes=json.loads((dest/'source-files-sha256.json').read_text())
source=dest/'source';source.mkdir()
with tarfile.open(archive) as tar:
    assert {{member.name for member in tar.getmembers()}}==set(hashes)
    for member in tar.getmembers():
        assert member.isfile() and not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
        assert hashlib.sha256(tar.extractfile(member).read()).hexdigest()==hashes[member.name]
    tar.extractall(source,filter='data')
print('Frozen source validated and extracted:',len(hashes),flush=True)
'''
remote(f'cd {REMOTE} && vendor/venv/bin/python -c ' + shlex.quote(code))
manifest = f'{DEST}/source/Cargo.toml'
build = f'{DEST}/build'
cargo = '/home/jules/.cargo/bin/cargo +1.97.1'
remote(f'cd {REMOTE} && {cargo} test --offline --locked --manifest-path {manifest} --target-dir {build} --lib --test walk_cli --test raw_negative_cli --test raw_schema --test raw_phase_diagnostics > {DEST}/tests.log 2>&1 && {cargo} build --release --offline --locked --manifest-path {manifest} --target-dir {build} --bin vass-reach > {DEST}/build.log 2>&1')
code = f'''
import hashlib,json,shutil,subprocess
from pathlib import Path
dest=Path({DEST!r})
shutil.copy2(dest/'build/release/vass-reach',dest/'vass-reach')
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
metadata=dict(source_sha256=sha(dest/'source.tar.gz'),binary_sha256=sha(dest/'vass-reach'),
    source_files=len(json.loads((dest/'source-files-sha256.json').read_text())),
    rustc=subprocess.check_output(['/home/jules/.cargo/bin/rustc','+1.97.1','--version','--verbose'],text=True),
    test_log_sha256=sha(dest/'tests.log'),build_log_sha256=sha(dest/'build.log'),
    commands={{'tests':{(cargo+' test --offline --locked --manifest-path '+manifest+' --target-dir '+build+' --lib --test walk_cli --test raw_negative_cli --test raw_schema --test raw_phase_diagnostics')!r},
              'build':{(cargo+' build --release --offline --locked --manifest-path '+manifest+' --target-dir '+build+' --bin vass-reach')!r}}})
(dest/'provenance.json').write_text(json.dumps(metadata,indent=2))
print(json.dumps(metadata,indent=2),flush=True)
'''
remote(f'cd {REMOTE} && vendor/venv/bin/python -c ' + shlex.quote(code))
