"""Extend the frozen validator with bounded finite-closure proof leaves."""
from pathlib import Path
import gzip
import hashlib
import io
import json
import tarfile

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT / 'results/runner-smpt-single-core-v2'
OUT = ROOT / 'results/runner-smpt-single-core-v3'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parents = json.loads((PARENT / 'files-sha256.json').read_text())
    payload = {name: (PARENT / 'source' / name).read_bytes() for name in parents}
    assert all(sha(payload[name]) == digest for name, digest in parents.items())
    name = 'scripts/benchmark.py'
    source = payload[name].decode()
    current = (ROOT / 'scripts/benchmark.py').read_text()
    helper = current[current.index('def finite_closure_size('):current.index('def verify_proof(')]
    source = source.replace('def verify_proof(', helper + 'def verify_proof(', 1)
    start = current.index("    if proof.get('kind') == 'finite-closure-v1':")
    end = current.index('    if not __debug__:', current.index("        return 'python-finite-closure'", start))
    block = current[start:end]
    start = source.index('    if not __debug__:', source.index('def verify_proof('))
    source = source[:start] + block + source[start:]
    start = source.index("        initial = tuple(problem['initial'])", source.index('def verify(problem,'))
    end = source.index("        return 'python-finite-closure'", start)
    source = source[:start] + "        if finite_closure_size(problem) is None: return 'none-checker-state-limit'\n" + source[end:]
    assert "kind == 'signed-threshold-invariant-v1'" in source
    assert "kind == 'phase-pair-closure-v1'" in source
    compile(source, name, 'exec')
    payload[name] = source.encode()
    OUT.mkdir()
    for name, data in payload.items():
        path = OUT / 'source' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    files = {name: sha(data) for name, data in sorted(payload.items())}
    changes = [name for name in files if parents[name] != files[name]]
    assert changes == ['scripts/benchmark.py']
    (OUT / 'files-sha256.json').write_text(json.dumps(files, indent=2) + '\n')
    with (OUT / 'runner.tar.gz').open('xb') as stream:
        with gzip.GzipFile(filename='', mode='wb', fileobj=stream, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode='w') as tar:
                for name, data in sorted(payload.items()):
                    info = tarfile.TarInfo(name)
                    info.size, info.mode, info.mtime = len(data), 0o644, 0
                    tar.addfile(info, io.BytesIO(data))
    provenance = dict(parent=str(PARENT.relative_to(ROOT)), parent_files=parents, files=files,
        changes=changes, archive_sha256=sha((OUT / 'runner.tar.gz').read_bytes()),
        preparer_sha256=sha(Path(__file__).read_bytes()),
        scope='Adds finite-closure-v1 proof verification, reuses bounded closure traversal for legacy answers, and preserves all prior proof formats. No solver command, scheduling, parser or resource-policy changes.')
    (OUT / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print(json.dumps(dict(files=len(files), archive_sha256=provenance['archive_sha256'])))


if __name__ == '__main__':
    main()
