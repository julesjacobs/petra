"""Resume the failed test build with the three separately pinned test fixtures."""
import hashlib
import json
from pathlib import Path
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[1]
HOST = 'jules@jules-b650-aorus-elite-ax-v2'
REMOTE = '/home/jules/experiments/pvass-publication'
DEST = 'results/linux-solver-repeated-search-v1'


def remote(command, **kwargs):
    return subprocess.run(['tailscale', 'ssh', HOST, command], check=True, **kwargs)


fixture_hashes = json.loads((ROOT / 'research/repeated-search-test-fixtures-v1.json').read_text())
for local, name in [('research/repeated-search-test-fixtures-v1.tar.gz', 'test-fixtures.tar.gz'),
                    ('research/repeated-search-test-fixtures-v1.json', 'test-fixtures-sha256.json')]:
    with (ROOT / local).open('rb') as stream:
        remote(f'cat > {REMOTE}/{DEST}/{name}', stdin=stream)
code = f'''
import hashlib,json,tarfile
from pathlib import Path
from scripts.process_runner import workspace_workloads
assert not workspace_workloads(Path.cwd())
dest=Path({DEST!r});source=dest/'source'
with tarfile.open(dest/'test-fixtures.tar.gz') as archive:
    assert {{m.name for m in archive.getmembers()}}==set({fixture_hashes!r})
    for m in archive.getmembers():
        assert m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts
        assert not (source/m.name).exists()
        assert hashlib.sha256(archive.extractfile(m).read()).hexdigest()=={fixture_hashes!r}[m.name]
    archive.extractall(source,filter='data')
(dest/'tests.log').rename(dest/'tests-initial-missing-fixtures.log')
print('Three test fixtures verified; initial failed build log preserved.',flush=True)
'''
remote(f'cd {REMOTE} && vendor/venv/bin/python -c ' + shlex.quote(code))
cargo = '/home/jules/.cargo/bin/cargo +1.97.1'
common = f'--offline --locked --manifest-path {DEST}/source/Cargo.toml --target-dir {DEST}/build'
commands = dict(tests=f'{cargo} test {common} --lib --test relaxed --test repeated_search',
                build=f'{cargo} build --release {common} --bin vass-reach')
remote(f"cd {REMOTE} && {commands['tests']} > {DEST}/tests.log 2>&1 && {commands['build']} > {DEST}/build.log 2>&1")
code = f'''
import hashlib,json,shutil,subprocess
from pathlib import Path
dest=Path({DEST!r})
shutil.copy2(dest/'build/release/vass-reach',dest/'vass-reach')
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
metadata=dict(source_sha256=sha(dest/'source.tar.gz'),binary_sha256=sha(dest/'vass-reach'),
    source_files=len(json.loads((dest/'source-files-sha256.json').read_text())),
    test_fixture_sha256={fixture_hashes!r},test_fixture_archive_sha256=sha(dest/'test-fixtures.tar.gz'),
    rustc=subprocess.check_output(['/home/jules/.cargo/bin/rustc','+1.97.1','--version','--verbose'],text=True),
    test_log_sha256=sha(dest/'tests.log'),build_log_sha256=sha(dest/'build.log'),
    commands={commands!r},
    qualification='Initial source archive lacked three compile-time test fixtures. Added separately pinned fixtures; initial failure preserved. Solver source archive unchanged.')
(dest/'provenance.json').write_text(json.dumps(metadata,indent=2)+'\\n')
print(json.dumps(metadata,indent=2),flush=True)
'''
remote(f'cd {REMOTE} && vendor/venv/bin/python -c ' + shlex.quote(code))
