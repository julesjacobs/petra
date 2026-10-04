"""Freeze signed-threshold dispatch without changing the active comparison runner."""
from pathlib import Path
import hashlib
import json
import shutil
import tarfile

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT / 'results/runner-phase-pair-v2'
OUT = ROOT / 'results/runner-threshold-v1'
HELPER = 'scripts/signed_threshold_checker.py'


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
        shutil.copyfile(PARENT / 'source' / name, target)
    shutil.copyfile(ROOT / HELPER, source / HELPER)
    dispatch = source / 'scripts/benchmark.py'
    text = dispatch.read_text()
    marker = "    if kind == 'phase-pair-closure-v1':"
    if text.count(marker) != 1:
        raise ValueError('Expected unique phase-pair dispatch marker')
    text = text.replace(marker,
        "    if kind == 'signed-threshold-invariant-v1':\n"
        "        from signed_threshold_checker import verify_signed_threshold\n"
        "        return verify_signed_threshold(problem, proof, deadline=_relevance_deadline)\n" + marker)
    dispatch.write_text(text)
    benchmark = source / 'scripts/benchmark_smpt_classic.py'
    text = benchmark.read_text()
    marker = "ROOT/'scripts/phase_pair_checker.py',"
    if text.count(marker) != 1:
        raise ValueError('Expected unique phase-pair source snapshot marker')
    benchmark.write_text(text.replace(marker, marker + " ROOT/'scripts/signed_threshold_checker.py',"))
    files = {name: sha(source / name) for name in sorted([*parents, HELPER])}
    changes = [name for name in parents if parents[name] != files[name]]
    if set(changes) != {'scripts/benchmark.py', 'scripts/benchmark_smpt_classic.py'}:
        raise ValueError(f'Unexpected runner changes: {changes}')
    (OUT / 'files-sha256.json').write_text(json.dumps(files, indent=2) + '\n')
    with tarfile.open(OUT / 'runner.tar.gz', 'w:gz') as archive:
        for name in files:
            archive.add(source / name, arcname=name, recursive=False)
    provenance = dict(parent='results/runner-phase-pair-v2', parent_files=parents, files=files,
                      archive_sha256=sha(OUT / 'runner.tar.gz'), changes=changes, additions=[HELPER],
                      scope='Opt-in supplied signed-threshold certificate checking; existing shared and frozen runners unchanged.')
    (OUT / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print(json.dumps(dict(files=len(files), changes=changes, additions=[HELPER], archive_sha256=provenance['archive_sha256'])))


if __name__ == '__main__':
    main()
