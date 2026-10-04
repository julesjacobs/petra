#!/usr/bin/env python3
"""Download and extract the published SMPT TACAS 2022 benchmark inputs."""
import argparse
import hashlib
import json
import pathlib
import subprocess
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
URL = 'https://zenodo.org/api/records/5863379/files/SMPT_TACAS_2022.zip/content'
SHA256 = '738608b17c7e698543cbcca9072aa6050a3e3e891074ec8b596b7fde66dbff48'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=pathlib.Path, default=ROOT/'vendor/smpt-benchmarks')
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    archive = args.directory/'SMPT_TACAS_2022.zip'
    if not archive.exists():
        temporary = archive.with_suffix('.zip.part')
        subprocess.run(['curl', '-L', '--fail', '--retry', '2', '--output', str(temporary), URL], check=True)
        if hashlib.file_digest(temporary.open('rb'), 'sha256').hexdigest() != SHA256:
            raise ValueError('Downloaded archive SHA-256 mismatch')
        temporary.replace(archive)
    with archive.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != SHA256:
            raise ValueError('Archive SHA-256 mismatch')
    output = args.directory/'tacas2022'
    files = []
    with zipfile.ZipFile(archive) as bundle:
        for info in bundle.infolist():
            relative = info.filename.removeprefix('SMPT_TACAS_2022/')
            selected = relative in ('Readme.txt', 'License.txt') or any(
                relative.startswith(f'Artifact/{suite}/')
                for suite in ('Performance', 'Expressiveness', 'Certificates'))
            if info.is_dir() or not selected:
                continue
            path = pathlib.PurePosixPath(relative)
            if path.is_absolute() or '..' in path.parts:
                raise ValueError(f'Unsafe archive path: {relative}')
            data = bundle.read(info)
            destination = output/path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            files.append(dict(path=relative, sha256=hashlib.sha256(data).hexdigest()))
    (args.directory/'provenance.json').write_text(json.dumps(dict(
        title='Property Directed Reachability for Generalized Petri Nets — TACAS 2022 artifact',
        doi='10.5281/zenodo.5863379', url=URL, archive_sha256=SHA256,
        license='See tacas2022/License.txt; original notices retained', files=files), indent=2)+'\n')
    print(f'Extracted {len(files)} files to {output}; archive checksum verified.')


if __name__ == '__main__':
    main()
