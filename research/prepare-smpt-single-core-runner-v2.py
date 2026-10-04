"""Add a workload scope independent of the isolated helper source root."""
from pathlib import Path
import gzip
import hashlib
import io
import json
import tarfile

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT / 'results/runner-smpt-single-core-v1'
OUT = ROOT / 'results/runner-smpt-single-core-v2'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parents = json.loads((PARENT / 'files-sha256.json').read_text())
    payload = {name: (PARENT / 'source' / name).read_bytes() for name in parents}
    assert all(sha(payload[name]) == digest for name, digest in parents.items())
    name = 'scripts/benchmark_smpt_classic.py'
    source = payload[name].decode()
    assert source.count('conflicts = workspace_workloads(ROOT)') == 2
    source = source.replace('conflicts = workspace_workloads(ROOT)',
                            "conflicts = workspace_workloads(getattr(args, 'workspace_root', ROOT))")
    marker = "    parser.add_argument('--corpus',"
    assert source.count(marker) == 1
    source = source.replace(marker,
        "    parser.add_argument('--workspace-root', type=pathlib.Path, default=ROOT,\n"
        "                        help='Workload conflict scope; helper imports and snapshots retain their source root')\n" + marker)
    marker = '    args = parser.parse_args()'
    assert source.count(marker) == 1
    source = source.replace(marker, marker + '\n    args.workspace_root = args.workspace_root.resolve()')
    marker = '    environment = dict(seconds=args.seconds,'
    assert source.count(marker) == 1
    source = source.replace(marker, "    environment = dict(workspace_root=str(args.workspace_root), seconds=args.seconds,")
    compile(source, name, 'exec')
    payload[name] = source.encode()
    OUT.mkdir()
    for name, data in payload.items():
        path = OUT / 'source' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    files = {name: sha(data) for name, data in sorted(payload.items())}
    changes = [name for name in files if parents[name] != files[name]]
    assert changes == ['scripts/benchmark_smpt_classic.py']
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
        scope='Adds explicit workload-preflight root; source/helper/snapshot root remains isolated. No scheduling, command, parsing or resource policy changes.')
    (OUT / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print(json.dumps(dict(files=len(files), archive_sha256=provenance['archive_sha256'])))


if __name__ == '__main__':
    main()
