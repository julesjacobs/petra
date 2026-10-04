"""Retest the unchanged built candidate after supplying missing test fixtures."""
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
assert sys.platform == 'linux' and str(ROOT) == '/home/jules/experiments/pvass-publication'
sys.path.insert(0, str(ROOT / 'scripts'))
from process_runner import workspace_workloads
assert not workspace_workloads(ROOT)
old = json.loads((F / 'build-receipt.json').read_text())
assert old['build']['exit_code'] == 0 and old['tests']['exit_code'] != 0
for name, digest in json.loads((F / 'candidate-source-sha256.json').read_text()).items():
    assert sha(SOURCE / name) == digest, name
for name, digest in json.loads((F / 'test-fixtures-sha256.json').read_text()).items():
    assert sha(ROOT / name) == digest, name
binary_before = sha(SOURCE / 'target/release/vass-reach')
env = dict(os.environ, PATH=str(Path.home() / '.cargo/bin') + ':' + os.environ['PATH'])
cmd = ['cargo', '+1.97.1', 'test', '--locked', '--offline', '--release']
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
with (F / 'tests-retry.log').open('x') as log:
    result = subprocess.run(cmd, cwd=SOURCE, env=env, stdout=log, stderr=subprocess.STDOUT)
assert sha(SOURCE / 'target/release/vass-reach') == binary_before
receipt = dict(old, previous_receipt_sha256=sha(F / 'build-receipt.json'),
               reason='Initial test compilation lacked three raw-harder fixture files; source and release binary unchanged.',
               tests=dict(command=cmd, exit_code=result.returncode, log_sha256=sha(F / 'tests-retry.log')),
               test_fixture_manifest_sha256=sha(F / 'test-fixtures-sha256.json'),
               exit_code=result.returncode, retry_started_utc=started,
               retry_finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
if result.returncode == 0:
    assert not (F / 'candidate-vass-reach').exists()
    shutil.copy2(SOURCE / 'target/release/vass-reach', F / 'candidate-vass-reach')
    receipt['binary_sha256'] = binary_before
with (F / 'build-receipt-v2.json').open('x') as out:
    json.dump(receipt, out, indent=2)
print(json.dumps(receipt), flush=True)
raise SystemExit(result.returncode)
