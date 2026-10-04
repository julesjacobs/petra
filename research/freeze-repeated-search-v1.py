import hashlib
import json
import shutil
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/solver-repeated-search-v1'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


OUT.mkdir()
names = set(json.loads((ROOT / 'results/solver-geometric-branches-v1/source-files-sha256.json').read_text()))
names.update([
    'src/repeat_fire.rs', 'tests/repeated_search.rs',
    'scripts/test_geometric_branch_scope.py', 'scripts/test_original_schedule_validation.py',
    'research/freeze-repeated-search-v1.py', 'research/run-repeated-search-gaps-v1.py',
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
for path in sorted((ROOT / 'research').glob('repeated-search-*.log')):
    shutil.copy2(path, review / path.name)
shutil.copy2(ROOT / 'research/repeated-search-contract.md', review / 'repeated-search-contract.md')
metadata = dict(
    change='Opt-in finite repeated-transition successors with normal expanded witnesses; default methods retain single-step successors.',
    binary_sha256=sha(OUT / 'vass-reach'), source_sha256=sha(OUT / 'source.tar.gz'),
    source_files=len(names), build='cargo build --release --locked --bin vass-reach',
    rustc=subprocess.check_output(['rustc', '--version', '--verbose'], text=True),
    validation='179 library tests, 13 existing relaxed tests and 6 repeated-search tests pass. Format, Clippy and release pass; existing vendor warnings. Initial test-call signature failures preserved and fixed.',
    performance='Not measured at freeze. Classical finite repeated firing; no novelty or dominance claim.',
    review_sha256={path.name: sha(path) for path in review.iterdir()},
)
(OUT / 'provenance.json').write_text(json.dumps(metadata, indent=2) + '\n')
print(json.dumps(metadata, indent=2))
