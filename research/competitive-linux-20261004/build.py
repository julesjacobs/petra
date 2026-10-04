"""Build and test the frozen candidate on Linux in a new directory."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

F = Path(__file__).resolve().parent
ROOT = F.parents[1]
SOURCE = F / 'candidate-source'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

assert sys.platform == 'linux'
assert str(ROOT) == '/home/jules/experiments/pvass-publication'
sys.path.insert(0, str(ROOT / 'scripts'))
from process_runner import workspace_workloads
assert not workspace_workloads(ROOT), 'Competing workspace workload'
pins = json.loads((F / 'candidate-source-sha256.json').read_text())
for name, digest in pins.items():
    assert sha(SOURCE / name) == digest, name
assert not (F / 'build-receipt.json').exists()
assert not (F / 'candidate-vass-reach').exists()
link = SOURCE / 'vendor/venv'
if not link.is_symlink():
    link.symlink_to(ROOT / 'vendor/venv', target_is_directory=True)
assert link.resolve() == (ROOT / 'vendor/venv').resolve()
fixtures = SOURCE / 'benchmarks'
if not fixtures.is_symlink():
    fixtures.symlink_to(ROOT / 'benchmarks', target_is_directory=True)
assert fixtures.resolve() == (ROOT / 'benchmarks').resolve()
env = dict(os.environ, PATH=str(Path.home() / '.cargo/bin') + ':' + os.environ['PATH'])
receipt = dict(started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
               source_manifest_sha256=sha(F / 'candidate-source-sha256.json'),
               script_sha256=sha(Path(__file__)),
               rustc=subprocess.check_output(['rustc', '+1.97.1', '-Vv'], env=env, text=True),
               cargo=subprocess.check_output(['cargo', '+1.97.1', '-V'], env=env, text=True))
commands = [
    ('build', ['cargo', '+1.97.1', 'build', '--locked', '--offline', '--release', '--bin', 'vass-reach']),
    ('tests', ['cargo', '+1.97.1', 'test', '--locked', '--offline', '--release']),
]
code = 0
for name, cmd in commands:
    with (F / (name + '.log')).open('x') as log:
        result = subprocess.run(cmd, cwd=SOURCE, env=env, stdout=log, stderr=subprocess.STDOUT)
    receipt[name] = dict(command=cmd, exit_code=result.returncode, log_sha256=sha(F / (name + '.log')))
    code = result.returncode
    if code:
        break
if not code:
    shutil.copy2(SOURCE / 'target/release/vass-reach', F / 'candidate-vass-reach')
    receipt['binary_sha256'] = sha(F / 'candidate-vass-reach')
receipt.update(exit_code=code, finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (F / 'build-receipt.json').open('x') as out:
    json.dump(receipt, out, indent=2)
print(json.dumps(receipt), flush=True)
raise SystemExit(code)
