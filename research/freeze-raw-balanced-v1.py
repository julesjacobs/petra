"""Build and freeze stable inputs for the opt-in adaptive candidate."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/solver-raw-balanced-v1"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


names = set(json.loads((ROOT / "results/solver-raw-proof-streaming-v1/source-files-sha256.json").read_text()))
names.update(str(path.relative_to(ROOT)) for folder in ["src", "tests"] for path in (ROOT / folder).rglob("*.rs"))
names.update(["research/freeze-raw-balanced-v1.py", "research/run-raw-balanced-pilot-v1.py",
              "scripts/benchmark_stress_raw.py", "scripts/raw_stress_worker.py"])
names.update(str(p.relative_to(ROOT)) for p in (ROOT / "scripts").glob("test_raw_*.py"))
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
for source in sorted((ROOT / "research").glob("raw-balanced-*.log")):
    shutil.copy2(source, OUT / source.name)
    logs[source.name] = sha(OUT / source.name)
metadata = dict(binary_sha256=sha(OUT / "vass-reach"), source_sha256=sha(OUT / "source.tar.gz"),
                source_files=len(names), source_stable_during_build=True,
                validation="See saved validation logs for exact commands, outcomes and test counts; no benchmark claim.",
                logs_sha256=logs, build_log_sha256=sha(OUT / "build.log"),
                rustc=subprocess.check_output(["rustc", "-Vv"], text=True),
                scope="Exact immutable control markings interned across game nodes and identity keys. Projection and certificate/checker semantics retained; extra interning work charged. Raw typed proofs serialized directly without a serde_json::Value copy; original JSON proof format unchanged. Adds opt-in raw-portfolio-balanced positive warmup and longer negative phase, and exact sparse duplicate-node checker keys. Legacy schedule retained. Work/state allowances are per-stage; wall/RSS limits are whole-query. No performance claim before matched pilot.")
(OUT / "provenance.json").write_text(json.dumps(metadata, indent=2) + "\n")
print(json.dumps(metadata, indent=2))
