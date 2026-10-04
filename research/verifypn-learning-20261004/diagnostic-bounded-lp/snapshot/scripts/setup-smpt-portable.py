#!/usr/bin/env python3
"""Pin upstream SMPT with plain WALK in place of unavailable internal slicing."""
import hashlib
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
COMMIT = '82206ddcca45ecc497f8ed8eebc169a7c69d3641'
source = ROOT/'vendor/SMPT-upstream'
destination = ROOT/'vendor/SMPT-portable'
if destination.exists():
    raise SystemExit('Portable checkout already exists; refusing to overwrite it')
destination.mkdir()
archive = subprocess.run(['git', '-C', str(source), 'archive', COMMIT], capture_output=True, check=True).stdout
subprocess.run(['tar', '-x', '-C', str(destination)], input=archive, check=True)
path = destination/'smpt/interfaces/walk.py'
original = path.read_text()
needle = 'self.slice: bool = slice'
assert original.count(needle) == 1
path.write_text(original.replace(needle, 'self.slice: bool = False  # Public Tina builds reject the internal slicing flags.'))
metadata = dict(upstream_commit=COMMIT, disabled_feature='WALK internal slicing',
                replacement='Walk on the supplied original net; Parikh guidance and all proof methods unchanged',
                reason='Official arm64 Tina 3.7.5 and 4.0.0 both reject the -rg reduction options used by upstream WALK',
                original_sha256=hashlib.sha256(original.encode()).hexdigest(),
                patched_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
(destination/'PORTABILITY.json').write_text(json.dumps(metadata, indent=2)+'\n')
print(destination)
