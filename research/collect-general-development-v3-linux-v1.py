"""Fetch the complete frozen Linux run only after authoritative termination."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FOLDER = Path('research/general-development-v3-linux-v1')
OUTPUT = Path('results/linux-general-development-v3-v1')
HOST = 'jules@jules-b650-aorus-elite-ax-v2'
REMOTE = '/home/jules/experiments/pvass-publication'
RECEIPTS = ['plan.json', 'dispatch.json', 'execution.json', 'terminal.json', 'capability.json', 'run.log']


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def ssh(code, **kwargs):
    return subprocess.run(['tailscale', 'ssh', HOST,
                           'cd '+shlex.quote(REMOTE)+' && vendor/venv/bin/python -c '+shlex.quote(code)],
                          check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Observe readiness without transferring results')
    parser.add_argument('--import-existing', action='store_true', help='Validate and import a previously downloaded archive without retransferring')
    args = parser.parse_args()
    plan_sha = sha(ROOT/FOLDER/'plan.json')
    dispatch = json.loads((ROOT/FOLDER/'dispatch.json').read_text())
    guard = f'''import json, psutil, sys, tarfile
from pathlib import Path
from scripts.process_runner import workspace_workloads
folder = Path({str(FOLDER)!r})
dispatch = json.loads((folder/'dispatch.json').read_text())
assert dispatch == {dispatch!r}, 'Dispatch identity changed'
try:
    p = psutil.Process(dispatch['pid'])
    live = p.create_time() == dispatch['created'] and p.status() != psutil.STATUS_ZOMBIE and Path('/proc/sys/kernel/random/boot_id').read_text().strip() == dispatch['boot_id']
except psutil.NoSuchProcess:
    live = False
terminal = json.loads((folder/'terminal.json').read_text()) if (folder/'terminal.json').exists() else None
ready = not live and terminal is not None and terminal.get('plan_sha256') == {plan_sha!r}
'''
    if args.check:
        ssh(guard + "print(json.dumps(dict(live=live, terminal=terminal, ready=ready)))\n")
        return
    sys.path.insert(0, str(ROOT/'scripts'))
    from process_runner import workspace_workloads
    if workspace_workloads(ROOT):
        raise RuntimeError('Local measurement still running; defer bulk transfer')
    archive = ROOT/FOLDER/'results.tar.gz'
    if (archive.exists() and not args.import_existing) or (ROOT/OUTPUT).exists():
        raise RuntimeError('Collection artifacts already exist; inspect them instead of overwriting')
    paths = [str(OUTPUT)] + [str(FOLDER/name) for name in RECEIPTS]
    transfer = guard + f'''
assert ready, 'Run is live or lacks a matching terminal receipt'
assert not workspace_workloads(Path.cwd()), 'Other Linux workload still running'
with tarfile.open(fileobj=sys.stdout.buffer, mode='w|gz') as archive:
    for path in {paths!r}:
        archive.add(path, arcname=path)
'''
    if not args.import_existing:
        with archive.open('xb') as stream:
            ssh(transfer, stdout=stream)
    else:
        assert archive.is_file(), 'No downloaded archive to import'
    with tempfile.TemporaryDirectory(prefix='pvass-linux-collection-') as temporary:
        staging = Path(temporary)
        with tarfile.open(archive) as source:
            members = source.getmembers()
            names = set()
            for member in members:
                path = Path(member.name)
                assert not path.is_absolute() and '..' not in path.parts
                assert member.isfile() or member.isdir()
                assert path == OUTPUT or path.is_relative_to(OUTPUT) or str(path) in paths[1:]
                assert member.name not in names, 'Duplicate archive member'
                names.add(member.name)
            source.extractall(staging, filter='data')
        files = sorted(p for p in staging.rglob('*') if p.is_file())
        identities = {str(p.relative_to(staging)): sha(p) for p in files}
        assert identities[str(FOLDER/'plan.json')] == plan_sha
        assert json.loads((staging/FOLDER/'dispatch.json').read_text()) == dispatch
        for receipt_name in ['execution.json', 'terminal.json']:
            assert json.loads((staging/FOLDER/receipt_name).read_text())['plan_sha256'] == plan_sha
        def destination_for(path):
            relative = path.relative_to(staging)
            destination = ROOT/relative
            if relative == FOLDER/'dispatch.json' and destination.exists() and sha(destination) != sha(path):
                assert json.loads(destination.read_text()) == json.loads(path.read_text())
                return ROOT/FOLDER/'remote-receipts'/'dispatch.json'
            return destination
        for path in files:
            destination = destination_for(path)
            if destination.exists():
                assert destination.is_file() and sha(destination) == sha(path), str(destination)
        imported_paths = {str(p.relative_to(staging)): str(destination_for(p).relative_to(ROOT)) for p in files}
        for path in files:
            destination = destination_for(path)
            if not destination.exists():
                destination.parent.mkdir(parents=True, exist_ok=True)
                with path.open('rb') as source, destination.open('xb') as target:
                    shutil.copyfileobj(source, target)
    receipt = dict(status='collected', archive=str(archive.relative_to(ROOT)),
                   archive_sha256=sha(archive), bytes=archive.stat().st_size,
                   files_sha256=identities, imported_paths=imported_paths, plan_sha256=plan_sha,
                   scope='Complete transfer; verdict and resource audit still required')
    with (ROOT/FOLDER/'collection.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(status='collected', files=len(identities), bytes=receipt['bytes'])))


if __name__ == '__main__':
    main()
