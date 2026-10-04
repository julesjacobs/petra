import hashlib
import json
import shutil
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/solver-geometric-branches-v1'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


OUT.mkdir()
names = set(json.loads((ROOT / 'results/solver-buffer-agglomeration-v2/source-files-sha256.json').read_text()))
names.update([
    'tests/original_schedule.rs', 'tests/original_schedule_cli.rs',
    'scripts/test_geometric_branch_scope.py', 'scripts/test_original_schedule_validation.py',
    'research/freeze-geometric-branches-v1.py', 'research/run-geometric-branches-gaps-v1.py',
])
hashes = {name: sha(ROOT / name) for name in sorted(names)}
(OUT / 'source-files-sha256.json').write_text(json.dumps(hashes, indent=2) + '\n')
with tarfile.open(OUT / 'source.tar.gz', 'w:gz') as archive:
    for name in sorted(names):
        archive.add(ROOT / name, arcname=name, recursive=False)
with tarfile.open(OUT / 'source.tar.gz', 'r:gz') as archive:
    assert {member.name for member in archive.getmembers()} == names
    for member in archive.getmembers():
        assert hashlib.sha256(archive.extractfile(member).read()).hexdigest() == hashes[member.name]
shutil.copy2(ROOT / 'target/release/vass-reach', OUT / 'vass-reach')
review = OUT / 'review'
review.mkdir()
for path in sorted((ROOT / 'research').glob('geometric-branches-*.log')):
    shutil.copy2(path, review / path.name)
shutil.copy2(ROOT / 'research/original-schedule-review.md', review / 'original-schedule-review.md')
metadata = dict(
    change='Opt-in geometric branch restarts; default and zero/single-branch scheduling unchanged.',
    binary_sha256=sha(OUT / 'vass-reach'), source_sha256=sha(OUT / 'source.tar.gz'),
    source_files=len(names), build='cargo build --release --locked --bin vass-reach',
    rustc=subprocess.check_output(['rustc', '--version', '--verbose'], text=True),
    validation='11 deterministic scheduler tests, 5 CLI test groups and 27 Python tests pass. Format and Clippy pass; existing vendor warnings. Initial CLI formatting failure preserved and fixed.',
    performance='Not measured at freeze. Review documents restart and ascending-order limitations.',
    review_sha256={path.name: sha(path) for path in review.iterdir()},
)
(OUT / 'provenance.json').write_text(json.dumps(metadata, indent=2) + '\n')
print(json.dumps(metadata, indent=2))
