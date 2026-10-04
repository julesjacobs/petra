"""Freeze the uniform-pair ablation over the checked phase-pair source archive."""
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT / "results/solver-phase-pair-v1"
OUT = ROOT / "results/solver-pair-ablation-v1"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    files = {}
    parent_hashes = json.loads((PARENT / "source-files-sha256.json").read_text())
    with tarfile.open(PARENT / "source.tar.gz") as archive:
        assert {m.name for m in archive.getmembers()} == set(parent_hashes)
        for member in archive.getmembers():
            data = archive.extractfile(member).read()
            assert hashlib.sha256(data).hexdigest() == parent_hashes[member.name]
            files[member.name] = data
    for name in ["src/main.rs", "src/phase_pair.rs", "tests/phase_pair.rs", "research/pair-ablation-v1-design.md", "research/freeze-pair-ablation-v1.py"]:
        files[name] = (ROOT / name).read_bytes()
    before = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())}
    for name, digest in before.items():
        assert sha(ROOT / name) == digest, f"Working source differs from frozen input: {name}"
    OUT.mkdir()
    with tarfile.open(OUT / "source.tar.gz", "w:gz") as archive:
        for name, data in sorted(files.items()):
            member = tarfile.TarInfo(name)
            member.size = len(data)
            member.mode = 0o644
            archive.addfile(member, io.BytesIO(data))
    (OUT / "source-files-sha256.json").write_text(json.dumps(before, indent=2) + "\n")
    with (OUT / "build.log").open("w") as log:
        subprocess.run(["cargo", "build", "--release", "--locked", "--bin", "vass-reach"],
                       cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    assert all(sha(ROOT / name) == digest for name, digest in before.items())
    shutil.copy2(ROOT / "target/release/vass-reach", OUT / "vass-reach")
    logs = {}
    for path in sorted((ROOT / "research").glob("pair-ablation-v1-*.log")):
        shutil.copy2(path, OUT / path.name)
        logs[path.name] = sha(path)
    metadata = dict(
        binary_sha256=sha(OUT / "vass-reach"), source_sha256=sha(OUT / "source.tar.gz"),
        source_files=len(files), parent_source_sha256=sha(PARENT / "source.tar.gz"),
        changed_parent_files=[name for name in parent_hashes if before[name] != parent_hashes[name]],
        source_stable_during_build=True, build_log_sha256=sha(OUT / "build.log"),
        validation_logs_sha256=logs,
        rustc=subprocess.check_output(["rustc", "-Vv"], text=True),
        scope="Adds opt-in uniform-pair ablation: same discovery, certificate and checkers, with empty landmarks. Existing phase-pair and portfolio schedules unchanged. No performance, novelty, completeness or superiority claim.",
    )
    assert metadata["changed_parent_files"] == ["src/main.rs", "src/phase_pair.rs", "tests/phase_pair.rs"]
    (OUT / "provenance.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
