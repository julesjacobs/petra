"""Read a terminal suite at idle priority; compress locally, then use frozen import checks."""
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
F = ROOT/'research/repeated-comparison-linux-v1'
REL = str(F.relative_to(ROOT))
OUT = 'results/linux-repeated-comparison-v1'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
dispatch = json.loads((F/'dispatch.json').read_text())
digest = sha(F/'suite.json')
archive = F/'results.tar.gz'
assert not archive.exists() and not (F/'collection.json').exists()
sys.path.insert(0, str(ROOT/'scripts'))
from process_runner import workspace_workloads
assert not workspace_workloads(ROOT)
code = f'''import hashlib,json,os,psutil,sys,tarfile,time
from pathlib import Path
assert os.sched_getaffinity(0)=={{9}} and psutil.Process().nice()==19
f=Path({REL!r}); d=json.loads((f/'dispatch.json').read_text()); assert d=={dispatch!r}
try:
 p=psutil.Process(d['pid']); live=p.create_time()==d['created'] and p.status()!=psutil.STATUS_ZOMBIE and Path('/proc/sys/kernel/random/boot_id').read_text().strip()==d['boot_id']
except psutil.NoSuchProcess: live=False
assert not live, 'Registered suite remains live'
assert hashlib.sha256((f/'suite.json').read_bytes()).hexdigest()=={digest!r}
t=json.loads((f/'terminal.json').read_text()); assert t['suite_sha256']=={digest!r} and t['exit_code']==0
assert t['completed']==[b['name'] for b in json.loads((f/'suite.json').read_text())['blocks']]
class Throttled:
 def __init__(self): self.start=time.monotonic(); self.bytes=0
 def write(self,data):
  sys.stdout.buffer.write(data); self.bytes+=len(data)
  delay=self.bytes/(2*1024*1024)-(time.monotonic()-self.start)
  if delay>0: time.sleep(delay)
with tarfile.open(fileobj=Throttled(),mode='w|') as tar:
 tar.add(str(f),arcname=str(f))
 tar.add({OUT!r},arcname={OUT!r})
'''
remote = 'cd /home/jules/experiments/pvass-publication && exec nice -n 19 ionice -c 3 taskset -c 9 vendor/venv/bin/python -c '+shlex.quote(code)
started = datetime.now(timezone.utc).isoformat()
with archive.open('xb') as target, gzip.GzipFile(fileobj=target,mode='wb',mtime=0) as compressed:
    process = subprocess.Popen(['tailscale','ssh','jules@jules-b650-aorus-elite-ax-v2',remote],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    while chunk := process.stdout.read(1024*1024):
        compressed.write(chunk)
    error = process.stderr.read().decode()
    assert process.wait()==0, error
receipt = dict(status='downloaded-for-frozen-import', started_utc=started,
    completed_utc=datetime.now(timezone.utc).isoformat(), suite_sha256=digest,
    archive_sha256=sha(archive), archive_bytes=archive.stat().st_size,
    script_sha256=sha(Path(__file__)), remote_nice=19, remote_io_priority='idle',
    remote_cpu=9, uncompressed_limit_bytes_per_second=2*1024*1024,
    compression='local gzip', remote_operation='read-only tar stream',
    reason='Other unrelated OxCaml builds and benchmarks active; collect completed results at idle priority without running benchmarks or modifying remote files.',
    note='The original collector remains unchanged; its --import-existing path validates suite, dispatch, execution, terminal, paths, and all existing local bytes.')
(F/'transfer-readonly-v1.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
