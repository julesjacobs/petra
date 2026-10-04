import hashlib
from pathlib import Path, PurePosixPath
import tarfile
root=Path('/home/jules/experiments/pvass-publication')
archive=root/'research/application-parameter-ladders-v2-deploy.tar.gz'
with archive.open('rb') as f:
    assert hashlib.file_digest(f,'sha256').hexdigest()=='415fee7023ec882eb9c70493377f37e14e3599d8e2b61feec1c75ab760f83f24'
allowed={'benchmarks/application-parameter-ladders-v2-selection.json',
         'research/application-parameter-ladders-v2-screen-plan.json',
         'research/run-linux-application-parameter-ladders-v2.sh',
         'research/prepare-application-ladders-v2-screen.py'}
with tarfile.open(archive,'r:gz') as t:
    members=t.getmembers(); names=set()
    for m in members:
        p=PurePosixPath(m.name)
        assert not p.is_absolute() and '..' not in p.parts and '\\' not in m.name
        assert m.isfile() or m.isdir()
        assert not m.issparse()
        assert m.name not in names; names.add(m.name)
        assert str(p) in allowed or p.is_relative_to('benchmarks/application-parameter-ladders-v2')
        assert not (root/p).exists(), f'Existing destination: {p}'
    t.extractall(root, members=members, filter='data')
print(f'Archive hash verified; safely extracted {len(members)} new members.')
