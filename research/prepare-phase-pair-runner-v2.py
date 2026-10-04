"""Freeze the v1 runner closure with complete phase-pair input schema checking."""
from pathlib import Path
import hashlib
import json
import shutil
import tarfile

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT / 'results/runner-phase-pair-v1'
OUT = ROOT / 'results/runner-phase-pair-v2'
HELPER = 'scripts/phase_pair_checker.py'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parents = json.loads((PARENT / 'files-sha256.json').read_text())
    for name, digest in parents.items():
        if sha(PARENT / 'source' / name) != digest:
            raise ValueError(f'Changed parent runner file: {name}')
    OUT.mkdir()
    source = OUT / 'source'
    source.mkdir()
    for name in parents:
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name if name == HELPER else PARENT / 'source' / name, target)
    files = {name: sha(source / name) for name in parents}
    changed = [name for name in parents if parents[name] != files[name]]
    if changed != [HELPER]:
        raise ValueError(f'Unexpected runner changes: {changed}')
    (OUT / 'files-sha256.json').write_text(json.dumps(files, indent=2) + '\n')
    with tarfile.open(OUT / 'runner.tar.gz', 'w:gz') as archive:
        for name in files:
            archive.add(source / name, arcname=name, recursive=False)
    provenance = dict(parent='results/runner-phase-pair-v1', parent_files=parents, files=files,
                      archive_sha256=sha(OUT / 'runner.tar.gz'), changes=changed,
                      scope='Schema alignment only; proof rule and existing historical runner unchanged.')
    (OUT / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print(json.dumps(dict(files=len(files), changes=changed, archive_sha256=provenance['archive_sha256'])))


if __name__ == '__main__':
    main()
