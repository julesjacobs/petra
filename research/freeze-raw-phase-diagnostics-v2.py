"""Freeze the built diagnostic candidate after tests; never build or run solvers."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/solver-raw-phase-diagnostics-v2"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


OUT.mkdir()
names = set(json.loads((ROOT / "results/solver-repeated-search-v1/source-files-sha256.json").read_text()))
names.update(json.loads((ROOT / "results/linux-solver-repeated-search-v1/test-fixtures-sha256.json").read_text()))
names.update(["src/raw_diagnostics.rs", "scripts/analyze_raw_phase_diagnostics.py",
              "scripts/test_raw_phase_diagnostics.py", "research/freeze-raw-phase-diagnostics-v2.py",
              "research/run-raw-phase-diagnostics-v2.py"])
hashes = {name: sha(ROOT / name) for name in sorted(names)}
(OUT / "source-files-sha256.json").write_text(json.dumps(hashes, indent=2) + "\n")
with tarfile.open(OUT / "source.tar.gz", "w:gz") as archive:
    for name in sorted(names):
        archive.add(ROOT / name, arcname=name, recursive=False)
with tarfile.open(OUT / "source.tar.gz") as archive:
    assert {member.name for member in archive.getmembers()} == names
    for member in archive.getmembers():
        assert hashlib.sha256(archive.extractfile(member).read()).hexdigest() == hashes[member.name]
shutil.copy2(ROOT / "target/release/vass-reach", OUT / "vass-reach")
metadata = dict(binary_sha256=sha(OUT / "vass-reach"), source_sha256=sha(OUT / "source.tar.gz"),
                source_files=len(names), rustc=subprocess.check_output(["rustc", "-Vv"], text=True),
                purpose="Opt-in progress diagnostics for raw reachability. No algorithmic improvement or competitive timing claim.")
(OUT / "provenance.json").write_text(json.dumps(metadata, indent=2) + "\n")
print(json.dumps(metadata, indent=2))
