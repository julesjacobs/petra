#!/usr/bin/env python3
"""Collect frozen SER stress exports under wall and sampled process-tree RSS limits.

Every attempt, log, and partial frontend artifact is retained. The frontend's
serial semilinear construction is charged here; this is not a solver benchmark.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import time

from process_runner import run, workspace_workloads

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def save(path, document):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(document, indent=2) + "\n")
    temporary.replace(path)


def artifact_guard(directory, limit, command):
    """Collection-local sampled disk guard; the outer runner owns tree cleanup."""
    child = subprocess.Popen(command)
    try:
        while True:
            total = 0
            for path in directory.rglob("*"):
                try:
                    if path.is_file():
                        total += path.stat().st_size
                except FileNotFoundError:
                    pass
            if total > limit:
                save(directory / "artifact-limit.json", dict(limit_bytes=limit, observed_bytes=total,
                                                             sampling_interval_seconds=0.05))
                if child.poll() is None:
                    child.kill()
                child.wait()
                return 125
            code = child.poll()
            if code is not None:
                return code
            time.sleep(0.05)
    finally:
        if child.poll() is None:
            child.kill()
        child.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "benchmarks/stress-programs/manifest.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frontend", type=Path, default=ROOT / "vendor/SerializabilityChecker/target/release/ser")
    parser.add_argument("--seconds", type=float, default=60)
    parser.add_argument("--memory-mib", type=int, default=2048)
    parser.add_argument("--artifact-mib", type=int, default=3072,
                        help="Sampled per-case source/log/work-file size limit; not a filesystem quota.")
    parser.add_argument("--case", action="append", help="Exact case name; repeat to select several.")
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or args.seconds <= 0 or min(args.memory_mib, args.artifact_mib) <= 0:
        parser.error("Resource limits must be positive and finite.")
    manifest_path = args.manifest.resolve()
    frontend = args.frontend.resolve(strict=True)
    manifest = json.loads(manifest_path.read_text())
    if manifest["format"] != "ser-stress-sources-v1":
        parser.error("Expected frozen ser-stress-sources-v1 manifest.")
    cases = manifest["cases"]
    if args.case:
        missing = set(args.case) - {case["name"] for case in cases}
        if missing:
            parser.error(f"Unknown cases: {sorted(missing)}")
        cases = [case for case in cases if case["name"] in args.case]
    for case in cases:
        source = manifest_path.parent / case["source"]
        if source.parent.resolve() != manifest_path.parent or source.stem != case["name"]:
            parser.error("Invalid case source path or name.")
        if sha256(source) != case["sha256"]:
            parser.error(f"Frozen source hash mismatch: {case['name']}")
    if workspace_workloads(ROOT):
        parser.error("Workspace solver/build workloads are active; defer collection until they finish.")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(manifest_path, output / "source-manifest.json")
    snapshot = output / "runner-source"
    snapshot.mkdir()
    for path in [Path(__file__), ROOT / "scripts/process_runner.py"]:
        shutil.copyfile(path, snapshot / path.name)
    report = dict(format="ser-stress-collection-v1", source_manifest_sha256=sha256(manifest_path),
                  frontend=str(frontend), frontend_sha256=sha256(frontend),
                  limits=dict(wall_seconds=args.seconds, sampled_process_tree_rss_bytes=args.memory_mib * 1024**2,
                              sampled_case_artifact_bytes=args.artifact_mib * 1024**2),
                  started_unix=time.time(),
                  selected_sources=[case["name"] for case in cases],
                  caveats=["RSS enforcement is sampled, not a Linux cgroup hard memory bound.",
                           "Short-lived children and between-sample peaks may escape accounting.",
                           "Artifact size is sampled, not a disk quota; excess bytes already written are retained.",
                           "Exported JSON is retained without unbounded parent-process JSON parsing.",
                           "Export status alone does not validate JSON semantics or establish a solver result."],
                  attempts=[])
    save(output / "collection.json", report)
    for case in cases:
        workloads = workspace_workloads(ROOT)
        if workloads:
            report["stopped"] = dict(reason="concurrent workspace workload", processes=workloads)
            save(output / "collection.json", report)
            raise SystemExit("Stopped before starting another frontend: concurrent workspace workload.")
        dest = output / case["name"]
        dest.mkdir()
        source = dest / case["source"]
        shutil.copyfile(manifest_path.parent / case["source"], source)
        work = dest / "work"
        work.mkdir()
        command = [str(frontend), "--export-raw", "--no-viz", str(source)]
        guarded_command = [sys.executable, str(Path(__file__).resolve()), "--artifact-guard", str(dest),
                           str(args.artifact_mib * 1024**2), *command]
        record = dict(name=case["name"], role=case["role"], exact_source_overlaps=case["exact_source_overlaps"],
                      source_sha256=case["sha256"], source_expectation=case["source_expectation"],
                      command=command, guarded_command=guarded_command,
                      status="running", started_unix=time.time(), solver_result=None)
        report["attempts"].append(record)
        save(output / "collection.json", report)
        try:
            wall, code, expired, usage = run(guarded_command, work, args.seconds, dest / "frontend.log",
                                             memory_bytes=args.memory_mib * 1024**2)
            emitted = work / "out" / source.stem / "raw-query.json"
            artifact_limit = dest / "artifact-limit.json"
            status = ("artifact-limit" if artifact_limit.exists() else
                      "memory-limit" if usage["memory_limit_exceeded"] else "timeout" if expired
                      else "exported-unvalidated" if code == 0 and emitted.is_file() else "frontend-error")
            record.update(status=status, wall_seconds=wall, exit_code=code, expired=expired, usage=usage)
            if artifact_limit.exists():
                record["artifact_limit"] = json.loads(artifact_limit.read_text())
            record["artifacts"] = []
            for path in sorted(work.rglob("*")):
                if path.is_file():
                    record["artifacts"].append(dict(path=str(path.relative_to(output)),
                                                     bytes=path.stat().st_size, sha256=sha256(path)))
            if emitted.is_file():
                record["query"] = str(emitted.relative_to(output))
            record["frontend_log_sha256"] = sha256(dest / "frontend.log")
        except BaseException as error:
            record.update(status="collection-interrupted", error=f"{type(error).__name__}: {error}")
            raise
        finally:
            record["finished_unix"] = time.time()
            save(output / "collection.json", report)
        print(case["name"], record["status"], flush=True)
    report["finished_unix"] = time.time()
    save(output / "collection.json", report)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--artifact-guard":
        raise SystemExit(artifact_guard(Path(sys.argv[2]), int(sys.argv[3]), sys.argv[4:]))
    main()
