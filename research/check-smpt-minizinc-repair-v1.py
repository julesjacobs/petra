"""Read-only identity preflight for the private Linux MiniZinc/SMPT capability."""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path('/home/jules/experiments/pvass-publication')
ARTIFACT = ROOT/'research/smpt-minizinc-repair-v1'


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


metadata = json.loads((ARTIFACT/'metadata.json').read_text())
bundle = Path(metadata['bundle'])
require(digest(ARTIFACT/'bundle-files-sha256.json') == metadata['bundle_manifest_sha256'], 'Bundle manifest changed')
files = json.loads((ARTIFACT/'bundle-files-sha256.json').read_text())
require({str(p.relative_to(bundle)) for p in bundle.rglob('*') if p.is_file()} == set(files), 'Bundle membership changed')
for name, expected in files.items():
    require(digest(bundle/name) == expected, 'Bundle file changed:'+name)
for name, record in metadata['shared_libraries'].items():
    require(str(Path(name).resolve()) == record['resolved'] and digest(name) == record['sha256'], 'Library changed:'+name)
for name, expected in metadata['tool_identities'].items():
    require(digest(name) == expected, 'Tool changed:'+name)
for name, expected in metadata['smpt_sources'].items():
    require(digest(ROOT/'vendor/SMPT-portable'/name) == expected, 'SMPT source changed:'+name)
for name, record in metadata['configuration_files'].items():
    path = Path(name)
    require(path.exists() == record['exists'], 'Configuration existence changed:'+name)
    if record.get('sha256'):
        require(digest(path) == record['sha256'], 'Configuration changed:'+name)
    if 'files' in record and path.exists():
        require({str(p):digest(p) for p in path.rglob('*') if p.is_file()} == record['files'], 'Configuration directory changed:'+name)
for key, value in metadata['inherited_minizinc_overrides'].items():
    require(os.environ.get(key) == value, 'MiniZinc environment changed:'+key)
require(digest(ROOT/'research/setup-smpt-minizinc-repair-v1.py') == metadata['script_sha256'], 'Setup script changed')
for label, record in metadata['records'].items():
    for stream in ('stdout','stderr'):
        require(digest(ARTIFACT/(label+'.'+stream)) == record[stream+'_sha256'], 'Smoke evidence changed:'+label)
for name, expected in metadata['smoke_inputs'].items():
    require(digest(ARTIFACT/name) == expected, 'Smoke input changed:'+name)
print(json.dumps(dict(status='identities-verified',bundle_files=len(files),shared_library_paths=len(metadata['shared_libraries']),default_solver=metadata['default_solver']),indent=2))
