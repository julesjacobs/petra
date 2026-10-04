#!/usr/bin/env python3
"""Extract and inspect the pinned FastForward runtime without executing it."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import struct
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'vendor/FastForward-artifact-v1/FastForward.zip'
ARCHIVE_SHA256 = '3424e0285729df073756e7947b710b3b7f55eb0d396d9781f32d5ad6872dd65f'
PREFIX = 'FastForward/artifact/benchmark/fastforward/'
Z3 = 'FastForward/dependencies/nuget/packages/microsoft.z3.x64/4.8.7/runtimes/ubuntu-x64/native/libz3.so'
MAX_MEMBER = 64 * 1024**2
MAX_TOTAL = 128 * 1024**2


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')


def elf_metadata(path):
    data = path.read_bytes()
    if not data.startswith(b'\x7fELF'):
        return None
    if data[4:6] != b'\x02\x01':
        raise ValueError(f'Expected ELF64 little endian: {path}')
    header = struct.unpack_from('<HHIQQQIHHHHHH', data, 16)
    kind, machine, _, _, phoff, shoff, _, _, phsize, phnum, shsize, shnum, _ = header
    if machine != 62:
        raise ValueError(f'Expected AMD64 ELF machine: {path}')
    def block(offset, length):
        if offset < 0 or length < 0 or offset + length > len(data):
            raise ValueError(f'ELF region outside file: {path}')
        return data[offset:offset+length]
    block(phoff, phsize*phnum)
    block(shoff, shsize*shnum)
    interpreter = None
    for i in range(phnum):
        ph = struct.unpack_from('<IIQQQQQQ', data, phoff+i*phsize)
        if ph[0] == 3:
            interpreter = block(ph[2], ph[5]).rstrip(b'\0').decode()
    sections = [struct.unpack_from('<IIQQQQIIQQ', data, shoff+i*shsize) for i in range(shnum)]
    needed, rpath, runpath = [], [], []
    for s in sections:
        if s[1] != 6:
            continue
        strings = sections[s[6]]
        names = block(strings[4], strings[5])
        dynamic = block(s[4], s[5])
        for offset in range(0, len(dynamic), 16):
            tag, value = struct.unpack_from('<qQ', dynamic, offset)
            if tag in (1, 15, 29):
                end = names.find(b'\0', value)
                if end < 0:
                    raise ValueError('Unterminated ELF dynamic string')
                text = names[value:end].decode()
                {1:needed, 15:rpath, 29:runpath}[tag].append(text)
    return dict(format='ELF64 little-endian', machine='AMD x86-64 (EM_X86_64=62)',
                elf_type=kind, interpreter=interpreter, needed=needed,
                rpath=rpath, runpath=runpath)


def preserve_notices(output):
    deps = json.loads((output/'runtime/fastforward.deps.json').read_text())
    packages = {k.lower() for k in deps['libraries']}
    packages.add('microsoft.netcore.app.runtime.linux-x64/3.1.9')
    prefix = 'FastForward/dependencies/nuget/packages/'
    fixed = {
        'FastForward/LICENSE.txt': 'notices/FastForward/LICENSE.txt',
        'FastForward/dependencies/z3/LICENSE.txt': 'notices/z3-bundled-4.8.9/LICENSE.txt',
        prefix+'microsoft.z3.x64/4.8.7/microsoft.z3.x64.nuspec': 'notices/microsoft.z3.x64/4.8.7/microsoft.z3.x64.nuspec',
    }
    records = []
    with zipfile.ZipFile(ARCHIVE) as archive:
        for info in archive.infolist():
            name = PurePosixPath(info.filename).name.lower()
            relative = fixed.get(info.filename)
            if info.filename.startswith(prefix):
                tail = info.filename[len(prefix):]
                parts = PurePosixPath(tail).parts
                if len(parts) == 3 and '/'.join(parts[:2]).lower() in packages and (
                        'license' in name or 'notice' in name):
                    relative = 'notices/nuget/' + tail
            if relative is None:
                continue
            if (info.file_size > 1024**2 or stat.S_ISLNK(info.external_attr>>16)
                    or '..' in PurePosixPath(relative).parts or info.flag_bits & 1):
                raise ValueError('Unsafe notice member')
            target = output / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write(archive.read(info))
            os.chmod(target, 0o644)
            records.append(dict(path=relative, archive_member=info.filename,
                                bytes=target.stat().st_size, sha256=digest(target)))
    result = dict(files=records,
                  z3_license_scope='The 4.8.7 NuGet archive has no embedded license file. '
                    'Its preserved nuspec pins the license URL to source commit '
                    '30e7c225cd510400eacd41d0a83e013b835a8ece. '
                    'The preserved standalone Z3 LICENSE comes from the separate bundled 4.8.9 distribution; '
                    'it is not claimed to be an authenticated 4.8.7 license. No network fetch performed.')
    write_json(output/'notice-manifest.json', result)
    return result


def prepare(output):
    if ARCHIVE.stat().st_size != 960594789 or digest(ARCHIVE) != ARCHIVE_SHA256:
        raise ValueError('Published archive identity mismatch')
    if output.exists() or output.is_symlink():
        raise ValueError('Refusing existing output')
    for parent in output.parents:
        if parent.is_symlink():
            raise ValueError(f'Symlink output ancestor: {parent}')
    entries, total, destinations = [], 0, set()
    with zipfile.ZipFile(ARCHIVE) as archive:
        for info in archive.infolist():
            if not (info.filename.startswith(PREFIX) or info.filename == Z3):
                continue
            parts = PurePosixPath(info.filename).parts
            mode = info.external_attr >> 16
            if (info.filename.startswith('/') or '\\' in info.filename or '..' in parts
                    or any(':' in p for p in parts) or stat.S_ISLNK(mode)
                    or stat.S_IFMT(mode) not in (0, stat.S_IFDIR, stat.S_IFREG)
                    or info.flag_bits & 1):
                raise ValueError(f'Unsafe archive entry: {info.filename}')
            relative = ('native/libz3.so' if info.filename == Z3 else
                        'runtime/' + info.filename[len(PREFIX):])
            destination = output / relative
            if destination in destinations:
                raise ValueError(f'Duplicate destination: {relative}')
            destinations.add(destination)
            if info.file_size > MAX_MEMBER:
                raise ValueError(f'Member too large: {info.filename}')
            total += info.file_size
            if total > MAX_TOTAL:
                raise ValueError('Extraction total too large')
            entries.append((info, destination))
        if not any(i.filename == Z3 for i, _ in entries):
            raise ValueError('Missing matching Z3 native member')
        if total != 116237181 or len(entries) != 318:
            raise ValueError(f'Unexpected runtime inventory: {len(entries)} entries, {total} bytes')
        output.mkdir(parents=False)
        records = []
        for info, destination in entries:
            if info.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            count = 0
            with archive.open(info) as source, destination.open('xb') as target:
                while chunk := source.read(1024**2):
                    count += len(chunk)
                    if count > info.file_size or count > MAX_MEMBER:
                        raise ValueError(f'Unexpected expanded size: {info.filename}')
                    target.write(chunk)
            if count != info.file_size:
                raise ValueError(f'Truncated member: {info.filename}')
            os.chmod(destination, 0o755 if destination.name == 'fastforward' else 0o644)
            records.append(dict(path=str(destination.relative_to(output)), archive_member=info.filename,
                                bytes=count, crc32=f'{info.CRC:08x}', sha256=digest(destination),
                                original_unix_mode=oct(info.external_attr>>16),
                                packaged_mode=oct(stat.S_IMODE(destination.stat().st_mode))))
    binaries = {}
    for record in records:
        path = output / record['path']
        with path.open('rb') as stream:
            magic = stream.read(4)
        if magic == b'\x7fELF':
            binaries[record['path']] = elf_metadata(path)
    provided = {Path(p).name for p in binaries}
    external = sorted({dep for info in binaries.values() for dep in info['needed']} - provided)
    runtime = json.loads((output/'runtime/fastforward.runtimeconfig.json').read_text())
    deps = json.loads((output/'runtime/fastforward.deps.json').read_text())
    metadata = dict(status='static-inspection-only; no binary executed', elf_files=binaries,
                    external_DT_NEEDED=external, runtime_config=runtime,
                    dependency_target=deps['runtimeTarget'],
                    z3_managed_entries={k:v for k,v in deps['libraries'].items() if 'z3' in k.lower()},
                    gurobi_entries=[k for k in deps['libraries'] if 'gurobi' in k.lower()],
                    caveat='DT_NEEDED does not enumerate dynamically loaded ICU, OpenSSL or all runtime dependencies; host compatibility is unverified.')
    write_json(output/'static-inspection.json', metadata)
    manifest = dict(format='fastforward-runtime-v1', status='prepared-not-executed',
                    source=dict(doi='10.6084/m9.figshare.13573592.v1',figshare_file_id=26048870,
                                archive_bytes=960594789,archive_sha256=ARCHIVE_SHA256),
                    extraction=dict(files=len(records), bytes=total,crc_checked=True,max_member_bytes=MAX_MEMBER,
                                    max_total_bytes=MAX_TOTAL,symlinks_allowed=False,
                                    scope='Only the complete archived runtime directory and matching NuGet Z3 4.8.7 native library.'),
                    files=sorted(records,key=lambda r:r['path']),generator_sha256=digest(Path(__file__)))
    write_json(output/'extraction-manifest.json', manifest)
    preserve_notices(output)
    print(json.dumps(dict(output=str(output),files=len(records),bytes=total,elf_files=len(binaries),external_DT_NEEDED=external)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'vendor/FastForward-runtime-v1')
    prepare(parser.parse_args().output.absolute())
