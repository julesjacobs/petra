"""Build and freeze stable inputs for the opt-in adaptive candidate."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/solver-raw-adaptive-v1"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


names = set(json.loads((ROOT / "results/solver-raw-phase-diagnostics-v2/source-files-sha256.json").read_text()))
names.update(str(path.relative_to(ROOT)) for folder in ["src", "tests"] for path in (ROOT / folder).rglob("*.rs"))
names.update(["research/freeze-raw-adaptive-v1.py", "research/run-raw-adaptive-pilot-v1.py",
              "scripts/benchmark_stress_raw.py", "scripts/raw_stress_worker.py"])
before = {name: sha(ROOT / name) for name in sorted(names)}
OUT.mkdir()
with (OUT / "build.log").open("w") as log:
    subprocess.run(["cargo", "build", "--release", "--locked", "--bin", "vass-reach"],
                   cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
assert all(sha(ROOT / name) == digest for name, digest in before.items())
(OUT / "source-files-sha256.json").write_text(json.dumps(before, indent=2) + "\n")
with tarfile.open(OUT / "source.tar.gz", "w:gz") as archive:
    for name in sorted(names):
        archive.add(ROOT / name, arcname=name, recursive=False)
with tarfile.open(OUT / "source.tar.gz") as archive:
    assert {m.name for m in archive.getmembers()} == names
    for member in archive.getmembers():
        assert hashlib.sha256(archive.extractfile(member).read()).hexdigest() == before[member.name]
shutil.copy2(ROOT / "target/release/vass-reach", OUT / "vass-reach")
logs = {}
for source in sorted((ROOT / "research").glob("raw-adaptive-*.log")):
    shutil.copy2(source, OUT / source.name)
    logs[source.name] = sha(OUT / source.name)
metadata = dict(binary_sha256=sha(OUT / "vass-reach"), source_sha256=sha(OUT / "source.tar.gz"),
                source_files=len(names), source_stable_during_build=True,
                validation="193 library tests; 7 raw CLI, 3 diagnostics and 2 raw schema integration tests; 20 raw harness tests; format, Clippy and release pass. Existing vendor warnings. Initial format differences retained in log.",
                logs_sha256=logs, build_log_sha256=sha(OUT / "build.log"),
                rustc=subprocess.check_output(["rustc", "-Vv"], text=True),
                scope="Opt-in causal adaptive control projection; existing default discovery and checkers retained. Repeated preparation charged per attempt; no shared-preparation or performance claim.")
(OUT / "provenance.json").write_text(json.dumps(metadata, indent=2) + "\n")
print(json.dumps(metadata, indent=2))
