#!/usr/bin/env python3
"""Input-inclusive raw stress runs; parent reads only bounded metadata, never queries."""
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import shutil
import sys
import time

from process_runner import run, workspace_workloads

ROOT = Path(__file__).resolve().parents[1]
METHODS = ["raw-bfs", "raw-search", "raw-potential", "raw-z3"]


def sha256(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def metadata(path, limit=16 * 1024**2):
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"Metadata exceeds parent size limit: {path}")
    return json.loads(data)


def inside(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Artifact path escapes collection")
    return path


def select_sources(corpus, names=None, all_sources=False):
    collection_path = corpus / "collection.json"
    collection = metadata(collection_path)
    manifest_path = corpus / "source-manifest.json"
    manifest = metadata(manifest_path)
    if collection.get("format") != "ser-stress-collection-v1" or manifest.get("format") != "ser-stress-sources-v1":
        raise ValueError("Expected stress collection and frozen source manifest")
    if sha256(manifest_path) != collection["source_manifest_sha256"]:
        raise ValueError("Source manifest hash mismatch")
    cases = manifest["cases"]
    manifest_names = [case["name"] for case in cases]
    if len(set(manifest_names)) != len(manifest_names):
        raise ValueError("Duplicate source in manifest")
    collection_names = collection.get("selected_sources", manifest_names)
    if (type(collection_names) is not list or any(type(name) is not str for name in collection_names)
            or len(set(collection_names)) != len(collection_names) or set(collection_names) - set(manifest_names)):
        raise ValueError("Invalid collection source selection")
    names = names if names is not None else manifest_names if all_sources else collection_names
    if set(names) - set(manifest_names):
        raise ValueError("Unknown selected source")
    attempts = {}
    for attempt in collection["attempts"]:
        if attempt["name"] in attempts:
            raise ValueError("Duplicate collection attempt")
        attempts[attempt["name"]] = attempt
    selected = []
    seen = set()
    for case in cases:
        name = case["name"]
        if name not in names:
            continue
        if name in seen or Path(name).name != name or name in ("", ".", ".."):
            raise ValueError("Invalid or duplicate source name")
        seen.add(name)
        attempt = attempts.get(name)
        record = dict(name=name, source_sha256=case["sha256"], role=case["role"],
                      source=str(inside(corpus, str(Path(name) / case["source"]))),
                      family=case.get("family"), parameters=case.get("parameters"),
                      exact_source_overlaps=case["exact_source_overlaps"], source_expectation=case["source_expectation"],
                      export_status=attempt["status"] if attempt else "not-collected")
        if attempt:
            record["export_attempt"] = attempt
        if attempt and attempt["source_sha256"] != case["sha256"]:
            record["availability"] = "source-hash-mismatch"
        elif not attempt or attempt["status"] != "exported-unvalidated":
            record["availability"] = "export-unavailable"
        else:
            query = attempt.get("query")
            artifacts = [a for a in attempt.get("artifacts", []) if a["path"] == query]
            if query is None or len(artifacts) != 1:
                record["availability"] = "missing-query-provenance"
            else:
                record.update(availability="pending-validation", query=str(inside(corpus, query)),
                              query_sha256=artifacts[0]["sha256"])
        selected.append(record)
    return selected


def freeze_inputs(sources, output):
    directory = output / "inputs"
    directory.mkdir()
    for source in sources:
        original_source = Path(source["source"])
        if original_source.exists():
            frozen_source = directory / (source["name"] + ".ser")
            try:
                shutil.copyfile(original_source, frozen_source)
                actual = sha256(frozen_source)
                source["source_snapshot_sha256"] = actual
                source["source_snapshot"] = str(frozen_source)
                if actual != source["source_sha256"] and source["availability"] == "pending-validation":
                    source["availability"] = "source-hash-mismatch"
            except OSError as error:
                source["source_snapshot_error"] = str(error)[:1000]
                if source["availability"] == "pending-validation":
                    source["availability"] = "source-unavailable"
        elif source["availability"] == "pending-validation":
            source["availability"] = "source-unavailable"
        frontend_log = original_source.parent / "frontend.log"
        if frontend_log.is_file():
            destination = directory / (source["name"] + ".frontend.log")
            try:
                shutil.copyfile(frontend_log, destination)
                actual = sha256(destination)
                source["frontend_log_sha256"] = actual
                expected = source.get("export_attempt", {}).get("frontend_log_sha256")
                source["frontend_log_provenance"] = ("hash-mismatch" if expected and actual != expected else
                                                     "checked" if expected else "hash-recorded-no-original-hash")
            except OSError as error:
                source["frontend_log_provenance"] = "unavailable"
                source["frontend_log_error"] = str(error)[:1000]
        if source["availability"] != "pending-validation":
            continue
        destination = directory / (source["name"] + ".json")
        try:
            shutil.copyfile(source["query"], destination)
            actual = sha256(destination)
            if actual != source["query_sha256"]:
                source.update(availability="input-hash-mismatch", observed_query_sha256=actual)
            else:
                source["frozen_query"] = str(destination)
        except OSError as error:
            source.update(availability="input-unavailable", error=str(error)[:1000])


def classify_worker(directory, code, expired, usage):
    if expired or code != 0:
        try:
            stage = metadata(directory / "progress.json", 4096).get("stage", "startup")
        except (ValueError, OSError, AttributeError):
            stage = "startup"
        status = "memory-limit" if usage.get("memory_limit_exceeded") else "outer-timeout" if expired else "worker-exit"
        return dict(verdict="unknown", status=status, stage=stage,
                    reason=f"bounded worker {status} during {stage}; no positive accepted")
    try:
        result = metadata(directory / "result.json", 32 * 1024)
        if not isinstance(result, dict) or result.get("verdict") not in ("reachable", "unknown"):
            raise ValueError("invalid worker result")
        if result["verdict"] == "reachable" and (result.get("status") != "verified-positive" or
                result.get("independent_check") != "python-original-replay-z3-nonmembership"):
            raise ValueError("unchecked positive")
        return result
    except (ValueError, OSError) as error:
        return dict(verdict="unknown", status="worker-protocol-error", reason=str(error)[:1000])


def classify_bounded_worker(directory, code, expired, usage, wall, seconds, memory_bytes):
    usage = dict(usage)
    # Exit can be observed before the runner checks a simultaneous limit.
    # Conservatively include teardown in the outer wall deadline.
    if usage["sampled_peak_rss_bytes"] > memory_bytes:
        usage["memory_limit_exceeded"] = True
    expired = expired or wall > seconds or usage["memory_limit_exceeded"]
    return classify_worker(directory, code, expired, usage), expired, usage


def report_text(sources, rows, methods, repeat, seconds):
    lines = ["# Raw stress comparison", "", f"{len(sources)} selected sources; {repeat} repetition(s); {seconds}s input-inclusive outer deadline.",
             "", "| Source availability | Count |", "|---|---:|"]
    counts = Counter((s["export_status"] if s["availability"] == "export-unavailable" else s["availability"]) for s in sources)
    lines.extend(f"| {status} | {count} |" for status, count in sorted(counts.items()))
    lines += ["", "| Method | Selected sources | Verified positive in every repetition | Unknown / incomplete repetitions | Not run: export/input unavailable |",
              "|---|---:|---:|---:|---:|"]
    for method in methods:
        groups = defaultdict(list)
        for row in rows:
            if row["method"] == method:
                groups[row["query"]].append(row)
        positive = sum(len(rs) == repeat and all(r["verdict"] == "reachable" for r in rs) for rs in groups.values())
        unavailable = sum(s["availability"] != "pending-validation" for s in sources)
        lines.append(f"| {method} | {len(sources)} | {positive} | {len(sources)-positive-unavailable} | {unavailable} |")
    lines += ["", "| Method | Invocation status | Count |", "|---|---|---:|"]
    statuses = Counter((row["method"], row.get("status", "unspecified")) for row in rows)
    lines.extend(f"| {method} | {status} | {count} |" for (method, status), count in sorted(statuses.items()))
    lines += ["", "Export failures remain in the selected-source denominator and are not solver unknowns. Input/schema failures, solver limits and verifier limits have distinct statuses in runs.jsonl.",
              "Only replayed positives with every original serial component refuted by Z3 are accepted. Z3 unknown, killed workers, and unsupported negative proofs are unknown.",
              "The single outer deadline includes interpreter startup, streamed hash checks, JSON/schema validation, solver startup/parsing/search, and independent checking. The solver phase receives 80% of remaining time by default; the remainder is reserved for checking. All worker/solver memory is counted together by sampled process-tree RSS.",
              "Frozen input preparation is outside timing. Export construction is recorded separately. This is sampled portable accounting, not cgroup isolation. raw-z3 is the direct quantified BMC script, not SMPT. Source expectations and bridge duplicates are not additional verified outcomes.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--methods", nargs="+", choices=METHODS, default=["raw-bfs", "raw-potential"])
    parser.add_argument("--seconds", type=float, default=5)
    parser.add_argument("--memory-mib", type=int, default=2048)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--solver-fraction", type=float, default=0.8)
    parser.add_argument("--max-states", type=int, default=200_000)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--case", action="append")
    selection.add_argument("--all-sources", action="store_true", help="Include the full source ladder beyond the collection selection.")
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or args.seconds <= 0 or min(args.memory_mib, args.repeat, args.max_states) <= 0 or not 0 < args.solver_fraction < 1:
        parser.error("Invalid time, memory, repetition, state, or solver-fraction bound")
    if len(set(args.methods)) != len(args.methods):
        parser.error("Duplicate method")
    if workspace_workloads(ROOT):
        parser.error("Workspace solver/build workload active")
    corpus, output, binary = args.corpus.resolve(), args.output.resolve(), args.binary.resolve(strict=True)
    collection_digest = sha256(corpus / "collection.json")
    manifest_digest = sha256(corpus / "source-manifest.json")
    sources = select_sources(corpus, args.case, args.all_sources)
    if not sources:
        parser.error("Empty selection")
    output.mkdir(parents=True, exist_ok=False)
    snapshot = output / "runner-source"
    snapshot.mkdir()
    source_hashes = {}
    for name in ["raw_stress_worker.py", "benchmark_stress_raw.py", "raw_z3.py", "process_runner.py"]:
        destination = snapshot / name
        shutil.copyfile(ROOT / "scripts" / name, destination)
        source_hashes[name] = sha256(destination)
    frozen_binary = output / "vass-reach"
    shutil.copy2(binary, frozen_binary)
    for name in ["collection.json", "source-manifest.json"]:
        shutil.copyfile(corpus / name, output / name)
    if sha256(output / "collection.json") != collection_digest or sha256(output / "source-manifest.json") != manifest_digest:
        raise ValueError("Collection metadata changed during preparation")
    freeze_inputs(sources, output)
    (output / "sources.json").write_text(json.dumps(sources, indent=2) + "\n")
    try:
        z3_version = importlib.metadata.version("z3-solver")
    except importlib.metadata.PackageNotFoundError:
        z3_version = "unavailable"
    environment = dict(corpus=str(corpus), collection_sha256=collection_digest,
                       source_manifest_sha256=manifest_digest,
                       source_selection="explicit-cases" if args.case else "full-manifest" if args.all_sources else "collection-selection",
                       selected_sources=[s["name"] for s in sources],
                       binary_source=str(binary), binary_sha256=sha256(frozen_binary), runner_sha256=source_hashes,
                       python=sys.version, python_executable=sys.executable, z3_package_version=z3_version,
                       methods=args.methods, repeat=args.repeat, seconds=args.seconds,
                       solver_fraction=args.solver_fraction, max_states=args.max_states,
                       memory_bytes=args.memory_mib * 1024**2, started_unix=time.time())
    (output / "environment.json").write_text(json.dumps(environment, indent=2) + "\n")
    rows = []
    with (output / "runs.jsonl").open("w") as records:
        for source in sources:
            for repetition in range(args.repeat):
                for method in args.methods if repetition % 2 == 0 else args.methods[::-1]:
                    row = dict(query=source["name"], method=method, repeat=repetition,
                               export_status=source["export_status"], availability=source["availability"],
                               verdict="not-run", status=source["availability"])
                    if source["availability"] == "pending-validation":
                        workloads = workspace_workloads(ROOT)
                        if workloads:
                            raise RuntimeError(f"Concurrent workspace workload before invocation: {workloads}")
                        directory = output / f"{source['name']}.{method}.{repetition}"
                        directory.mkdir()
                        command = [sys.executable, str(snapshot / "raw_stress_worker.py"),
                                   "--query", source["frozen_query"], "--sha256", source["query_sha256"],
                                   "--directory", str(directory), "--binary", str(frozen_binary),
                                   "--raw-z3", str(snapshot / "raw_z3.py"), "--method", method,
                                   "--seconds", str(args.seconds), "--solver-fraction", str(args.solver_fraction),
                                   "--max-states", str(args.max_states)]
                        wall, code, expired, usage = run(command, ROOT, args.seconds, directory / "worker.log",
                                                         memory_bytes=args.memory_mib * 1024**2)
                        result, expired, usage = classify_bounded_worker(
                            directory, code, expired, usage, wall, args.seconds, args.memory_mib * 1024**2)
                        row.update(result)
                        row.update(wall_seconds=wall, worker_exit_code=code, outer_timeout=expired, usage=usage,
                                   query_sha256=source["query_sha256"], command=command)
                    records.write(json.dumps(row) + "\n")
                    records.flush()
                    rows.append(row)
                    (output / "REPORT.md").write_text(report_text(sources, rows, args.methods, args.repeat, args.seconds))
                    print(source["name"], method, repetition, row["status"], flush=True)


if __name__ == "__main__":
    main()
