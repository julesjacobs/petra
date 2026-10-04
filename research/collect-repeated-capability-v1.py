"""Fetch fresh repeated-comparison capability artifacts while both gates are idle."""
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile

ROOT=Path(__file__).resolve().parents[1]
F=ROOT/'research/repeated-comparison-linux-v1'
sys.path.insert(0,str(ROOT/'scripts'))
from process_runner import workspace_workloads
assert not workspace_workloads(ROOT)
suite=json.loads((F/'suite.json').read_text())
paths=[str((F/'qualification.json').relative_to(ROOT))]
paths += [str((F/b['name']).relative_to(ROOT)) for b in suite['blocks']]
paths += [f'{prefix}/repeated-capability-{budget}s-v1' for budget in [5,30] for prefix in ['benchmarks']]
paths += [f'results/linux-repeated-capability-{budget}s-v1' for budget in [5,30]]
code=f'''import json,sys,tarfile
from pathlib import Path
from scripts.process_runner import workspace_workloads
assert not workspace_workloads(Path.cwd())
f=Path('research/repeated-comparison-linux-v1')
assert not (f/'dispatch.json').exists()
assert json.loads((f/'qualification.json').read_text())['status']=='passed'
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as tar:
 for path in {paths!r}:tar.add(path,arcname=path)
'''
archive=F/'capability-evidence.tar.gz'
with archive.open('xb') as out:
    subprocess.run(['tailscale','ssh','jules@jules-b650-aorus-elite-ax-v2',
                    'cd /home/jules/experiments/pvass-publication && vendor/venv/bin/python -c '+shlex.quote(code)],stdout=out,check=True)
pins={}
with tarfile.open(archive) as tar:
    for item in tar:
        p=Path(item.name)
        assert not p.is_absolute() and '..' not in p.parts
        if item.isdir():continue
        assert item.isfile(),item.name
        data=tar.extractfile(item).read()
        dest=ROOT/p
        if dest.exists():assert dest.read_bytes()==data,item.name
        else:
            dest.parent.mkdir(parents=True,exist_ok=True)
            with dest.open('xb') as out:out.write(data)
        pins[item.name]=hashlib.sha256(data).hexdigest()
receipt=dict(status='collected',files_sha256=pins,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
(F/'capability-collection.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(dict(status='collected',files=len(pins),archive_sha256=receipt['archive_sha256'])))
