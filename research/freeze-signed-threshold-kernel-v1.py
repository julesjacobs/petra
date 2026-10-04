"""Archive the tested supplied-invariant kernel; this is not a timed solver build."""
import hashlib
import io
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT / 'results/solver-capacity-combinations-v1'
OUT = ROOT / 'results/kernel-signed-threshold-v1'

def sha(data):
    return hashlib.sha256(data).hexdigest()

parent = json.loads((PARENT/'source-files-sha256.json').read_text())
files = {name:(ROOT/name).read_bytes() for name in parent}
for name in ['src/signed_threshold.rs', 'scripts/signed_threshold_checker.py',
             'tests/signed_threshold.rs', 'tests/check_signed_threshold.py',
             'tests/check_phase_pair_schema.py', 'research/signed-threshold-v1-contract.md',
             'research/signed-threshold-v1-experiment.md', 'research/freeze-signed-threshold-kernel-v1.py']:
    files[name] = (ROOT/name).read_bytes()
OUT.mkdir()
with tarfile.open(OUT/'source.tar.gz','w:gz') as archive:
    for name,data in sorted(files.items()):
        member=tarfile.TarInfo(name);member.size=len(data);member.mode=0o644
        archive.addfile(member,io.BytesIO(data))
listing={name:sha(data) for name,data in sorted(files.items())}
(OUT/'source-files-sha256.json').write_text(json.dumps(listing,indent=2)+'\n')
logs={}
for suffix in ['validation','python','clippy','format']:
    name=f'signed-threshold-v1-{suffix}.log'
    data=(ROOT/'research'/name).read_bytes();(OUT/name).write_bytes(data);logs[name]=sha(data)
provenance=dict(kind='supplied-kernel-source-v1', source_sha256=sha((OUT/'source.tar.gz').read_bytes()),
    parent_source_sha256=sha((PARENT/'source.tar.gz').read_bytes()),
    changed_parent_files=[name for name,digest in parent.items() if listing[name]!=digest],
    files=len(files), validation_logs_sha256=logs,
    validation='242 Rust tests;15 Python threshold tests;7 Python phase-schema/composition tests separately recorded; formatting and project Clippy passed.',
    scope='Supplied-invariant correctness kernel only. No automatic discovery, new corpus result, speed claim or release binary in this package.')
(OUT/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
with tarfile.open(OUT/'source.tar.gz') as archive:
    assert {m.name for m in archive.getmembers()} == set(listing)
    for member in archive.getmembers():
        assert sha(archive.extractfile(member).read()) == listing[member.name]
print(json.dumps(provenance,indent=2))
