#!/usr/bin/env python3
"""Package the original research files without changing frozen experiments."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('PETRA_ARCHIVE_DIR', ROOT.parent / 'petra-artifacts')).resolve()
PRIVATE = {
    'research/pro-coverage-20261004/submitted.png',
    'research/pro-pair-review-v1/submitted.png',
    'research/pro-direction-review-v1/submitted.png',
}
CACHE = {
    'vendor/venv', 'vendor/SerializabilityChecker/target',
    'vendor/verifypn/build-release', 'vendor/KReach/dist-newstyle',
}
EXTRA = [
    'target/release/vass-reach',
    'vendor/SerializabilityChecker/target/release/ser',
    'vendor/verifypn/build-release/verifypn/bin/verifypn-osx64',
    'vendor/verifypn/build-release/verifypn/bin/verifypn',
    'vendor/venv/bin/z3',
]


def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def files(base):
    for directory, directories, names in os.walk(ROOT / base, followlinks=False):
        relative = Path(directory).relative_to(ROOT)
        directories[:] = sorted(d for d in directories
            if d not in {'.git', '__pycache__', 'autom4te.cache', '.deps', '.libs'}
            and (relative / d).as_posix() not in CACHE)
        for name in sorted(names):
            path = relative / name
            if name in {'.DS_Store', '.pvass-measurement.lock'} or name.endswith(('.pyc', '.pyo')):
                continue
            if path.as_posix() not in PRIVATE:
                yield path
        for name in directories[:]:
            path = relative / name
            if (ROOT / path).is_symlink():
                yield path
                directories.remove(name)


def package(name, paths):
    destination = OUT / f'petra-{name}.tar.zst'
    if destination.exists():
        raise FileExistsError(destination)
    count = total = 0
    manifest = OUT / f'petra-{name}.files.jsonl'
    with destination.open('xb') as stream, manifest.open('x') as inventory:
        compressor = subprocess.Popen(['zstd', '-q', '-T2', '-3', '-c'], stdin=subprocess.PIPE, stdout=stream)
        try:
            with tarfile.open(fileobj=compressor.stdin, mode='w|', format=tarfile.PAX_FORMAT) as archive:
                for relative in sorted(set(paths)):
                    path = ROOT / relative
                    info = archive.gettarinfo(str(path), arcname=relative.as_posix())
                    info.uid = info.gid = 0
                    info.uname = info.gname = ''
                    record = dict(path=relative.as_posix(), size=info.size, mode=info.mode, type='file' if info.isfile() else 'symlink')
                    if info.isfile():
                        before = path.stat()
                        record['sha256'] = digest(path)
                        with path.open('rb') as data:
                            archive.addfile(info, data)
                        after = path.stat()
                        assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), path
                        total += info.size
                    elif info.issym():
                        record['target'] = info.linkname
                        archive.addfile(info)
                    else:
                        raise ValueError((path, info.type))
                    inventory.write(json.dumps(record, sort_keys=True) + '\n')
                    count += 1
            compressor.stdin.close()
            if compressor.wait() != 0:
                raise RuntimeError('Compression failed')
        finally:
            if compressor.poll() is None:
                compressor.kill()
                compressor.wait()
    subprocess.run(['zstd', '-q', '-3', '--rm', str(manifest)], check=True)
    result = dict(name=destination.name, bytes=destination.stat().st_size,
                  sha256=digest(destination), files=count, uncompressed_bytes=total,
                  inventory=manifest.name + '.zst', inventory_sha256=digest(Path(str(manifest)+'.zst')))
    print(json.dumps(result), flush=True)
    return result


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    for base in ['benchmarks', 'results', 'research', 'vendor']:
        records.append(package(base, files(base)))
    runtimes = [Path(p) for p in EXTRA]
    runtimes += list(files('out'))
    for p in (ROOT / 'vendor/venv/lib').glob('python*/site-packages/z3_solver-*.dist-info/licenses/**'):
        if p.is_file():
            runtimes.append(p.relative_to(ROOT))
    records.append(package('runtimes', runtimes))
    result = dict(format='petra-research-release-v1', tag='research-2026-10-04',
                  repository='julesjacobs/petra', archives=records,
                  excluded_categories=['compiler and dependency build caches', 'Git metadata', 'Python virtual environment except pinned Z3 binary and license', 'Python bytecode', 'three screenshots of unrelated private chats'],
                  private_screenshots=sorted(PRIVATE))
    (ROOT / 'publication/artifacts.json').write_text(json.dumps(result, indent=2)+'\n')
    with (OUT / 'SHA256SUMS').open('x') as f:
        for p in sorted(OUT.glob('*.zst')):
            f.write(f'{digest(p)}  {p.name}\n')
