"""Repair packaging without changing any file in the original frozen source."""
import ast
import hashlib
import io
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "results/solver-walk-sparse-v1"
OUT = ROOT / "results/solver-walk-sparse-v2"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    hashes = json.loads((OLD / "source-files-sha256.json").read_text())
    files = {}
    with tarfile.open(OLD / "source.tar.gz") as archive:
        assert {m.name for m in archive.getmembers()} == set(hashes)
        for member in archive.getmembers():
            assert member.isfile() and not Path(member.name).is_absolute()
            assert ".." not in Path(member.name).parts
            data = archive.extractfile(member).read()
            assert sha(data) == hashes[member.name]
            files[member.name] = data
    additions = {}
    # Include the complete small script directory, including requirements and
    # lazy-imported independent checkers, rather than a hand-maintained subset.
    for path in sorted((ROOT / "scripts").iterdir()):
        if not path.is_file():
            continue
        name = str(path.relative_to(ROOT))
        data = path.read_bytes()
        if name in files:
            assert data == files[name], f"Changed frozen dependency: {name}"
        else:
            files[name] = data
            additions[name] = sha(data)
    modules = {Path(name).stem for name in files if name.startswith("scripts/") and name.endswith(".py")}
    edges = {}
    for name, data in files.items():
        if name.startswith("scripts/") and name.endswith(".py"):
            imported = set()
            for node in ast.walk(ast.parse(data, filename=name)):
                if isinstance(node, ast.Import):
                    imported.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".")[0])
            edges[name] = sorted(imported & modules)
            assert all(f"scripts/{module}.py" in files for module in edges[name])
    OUT.mkdir()
    with tarfile.open(OUT / "source.tar.gz", "w:gz") as archive:
        for name, data in sorted(files.items()):
            member = tarfile.TarInfo(name)
            member.size = len(data)
            member.mode = 0o644
            archive.addfile(member, io.BytesIO(data))
    all_hashes = {name: sha(data) for name, data in sorted(files.items())}
    (OUT / "source-files-sha256.json").write_text(json.dumps(all_hashes, indent=2) + "\n")
    provenance = dict(
        reason="v1 Linux tests could not import omitted raw_invariant_check.py; original failed archive and logs retained",
        parent_archive="results/solver-walk-sparse-v1/source.tar.gz",
        parent_sha256=sha((OLD / "source.tar.gz").read_bytes()),
        original_files_preserved=len(hashes), added_files=additions,
        source_sha256=sha((OUT / "source.tar.gz").read_bytes()),
        script_local_imports=edges,
        packaging_script_sha256=sha(Path(__file__).read_bytes()),
        scope="Packaging repair only; all Rust source, tests, fixtures, Cargo lock and patched varisat are byte-identical to v1. No benchmark result.",
    )
    (OUT / "packaging-provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(json.dumps({k: v for k, v in provenance.items() if k not in ("added_files", "script_local_imports")}, indent=2))
    print("Added", len(additions), "files; total", len(files))


if __name__ == "__main__":
    main()
