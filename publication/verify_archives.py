#!/usr/bin/env python3
"""Check archive bytes and every member against the published inventories."""
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tarfile

manifest = json.loads((Path(__file__).parent / 'artifacts.json').read_text())
folder = Path(sys.argv[1])
for entry in manifest['archives']:
    archive = folder / entry['name']
    inventory = folder / entry['inventory']
    for path, expected in [(archive, entry['sha256']), (inventory, entry['inventory_sha256'])]:
        with path.open('rb') as data:
            assert hashlib.file_digest(data, 'sha256').hexdigest() == expected, path
    assert archive.stat().st_size == entry['bytes'] < 2 * 1024**3
    a = subprocess.Popen(['zstd', '-qdc', str(archive)], stdout=subprocess.PIPE)
    i = subprocess.Popen(['zstd', '-qdc', str(inventory)], stdout=subprocess.PIPE, text=True)
    count = total = 0
    try:
        with tarfile.open(fileobj=a.stdout, mode='r|') as stream:
            for member, line in itertools.zip_longest(stream, i.stdout):
                assert member is not None and line is not None
                record = json.loads(line)
                assert member.name == record['path']
                assert member.mode == (record['mode'] & 0o7777)
                assert member.size == record['size']
                assert member.name not in manifest['private_screenshots']
                if record['type'] == 'file':
                    assert member.isfile()
                    digest = hashlib.sha256()
                    data = stream.extractfile(member)
                    while chunk := data.read(1024 * 1024):
                        digest.update(chunk)
                    assert digest.hexdigest() == record['sha256'], member.name
                    total += member.size
                else:
                    assert member.issym() and member.linkname == record['target']
                count += 1
        assert a.wait() == i.wait() == 0
        assert count == entry['files'] and total == entry['uncompressed_bytes']
        print(entry['name'], count, 'files verified', flush=True)
    finally:
        for process in [a, i]:
            if process.poll() is None:
                process.kill()
                process.wait()
