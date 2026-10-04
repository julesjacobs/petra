"""Register and qualify all corrected transfer sources after collection terminates."""
import hashlib
import importlib.util
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from process_runner import workspace_workloads


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path, data):
    with path.open("x") as stream:
        json.dump(data, stream, indent=2)
        stream.write("\n")


def main():
    corpus = ROOT / "benchmarks/raw-transfer-automaton-v2"
    collection = json.loads((corpus / "collection.json").read_text())
    sources = json.loads((corpus / "source-manifest.json").read_text())["cases"]
    names = [source["name"] for source in sources]
    assert "finished_unix" in collection and len(names) == len(set(names)) == 12
    assert collection["selected_sources"] == names
    assert [attempt["name"] for attempt in collection["attempts"]] == names
    assert all(attempt["status"] != "running" for attempt in collection["attempts"])
    assert sha(corpus / "source-manifest.json") == collection["source_manifest_sha256"]
    attempts = {attempt["name"]: attempt for attempt in collection["attempts"]}
    binary = ROOT / "results/solver-raw-balanced-v1/vass-reach"
    provenance = json.loads(binary.with_name("provenance.json").read_text())
    assert sha(binary) == provenance["binary_sha256"]
    assert sha(binary.with_name("source.tar.gz")) == provenance["source_sha256"]
    assert not workspace_workloads(ROOT)
    output = ROOT / "results/transfer-raw-pilot-v1"
    assert not output.exists()
    methods = ["raw-portfolio", "raw-portfolio-balanced"]
    command = [sys.executable, "scripts/benchmark_stress_raw.py", "--corpus", str(corpus),
               "--output", str(output), "--binary", str(binary), "--methods", *methods,
               "--all-sources", "--seconds", "60", "--memory-mib", "2048", "--repeat", "1",
               "--solver-fraction", "0.8", "--max-states", "100000000"]
    runner_names = json.loads((ROOT / "results/raw-balanced-cohorts-v1-diverse/environment.json").read_text())["runner_sha256"]
    paths = [ROOT / "scripts" / name for name in runner_names]
    paths += [Path(__file__), corpus / "collection.json", corpus / "source-manifest.json",
              binary.with_name("provenance.json"),
              ROOT / "research/transfer-raw-collection-v2-plan.json"]
    for source in sources:
        attempt = attempts[source["name"]]
        path = corpus / source["name"] / source["source"]
        assert sha(path) == source["sha256"] == attempt["source_sha256"]
        paths.append(path)
        for artifact in attempt["artifacts"]:
            path = corpus / artifact["path"]
            assert sha(path) == artifact["sha256"]
            paths.append(path)
    pins = {str(path.relative_to(ROOT)): sha(path) for path in paths}
    plan = dict(format="transfer-raw-pilot-v1", sources=names, source_slots=12, expected_rows=24,
                methods=methods, command=command, binary_sha256=provenance["binary_sha256"],
                source_archive_sha256=provenance["source_sha256"], file_sha256=pins,
                limits=dict(seconds=60, memory_mib=2048, solver_fraction=0.8, max_states=100000000,
                            negative_check_work=10000000000, repeat=1),
                scope="Complete corrected transfer cohort, including every export failure. Matched legacy/balanced schedules in one frozen Rust binary, same independent checker, 60s input/check-inclusive outer budget and sampled2GiB. No other local solver/build/export job. Per-stage work limits are not aggregate instructions. Source expectations are not reference answers; raw-z3 does not support automaton targets and is not a competitor here. Local development qualification, not competitive timing.")
    plan_path = ROOT / "research/transfer-raw-pilot-v1-plan.json"
    save(plan_path, plan)
    environment = dict(os.environ)
    for name in ("VASS_RAW_PHASE_DIAGNOSTICS", "VASS_RAW_NEGATIVE_DIAGNOSTICS"):
        environment.pop(name, None)
    assert all(sha(ROOT / name) == digest for name, digest in pins.items())
    code = subprocess.run(command, cwd=ROOT, env=environment).returncode
    save(ROOT / "research/transfer-raw-pilot-v1-terminal.json", dict(exit_code=code))
    assert code == 0, "Retain failed harness artifacts for investigation"
    recorded = json.loads((output / "environment.json").read_text())
    assert recorded["selected_sources"] == names and recorded["methods"] == methods
    assert recorded["binary_sha256"] == sha(output / "vass-reach") == plan["binary_sha256"]
    for name, digest in recorded["runner_sha256"].items():
        assert sha(output / "runner-source" / name) == digest == pins["scripts/" + name]
    spec = importlib.util.spec_from_file_location("frozen_transfer_classifier", output / "runner-source/benchmark_stress_raw.py")
    classifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(classifier)
    rows = [json.loads(line) for line in (output / "runs.jsonl").read_text().splitlines()]
    assert len(rows) == 24 and {(r["query"], r["method"], r["repeat"]) for r in rows} == {
        (name, method, 0) for name in names for method in methods}
    verdicts = defaultdict(set)
    for row in rows:
        attempt = attempts[row["query"]]
        verdicts[row["query"]].add(row["verdict"])
        if attempt["status"] != "exported-unvalidated":
            assert row["status"] == "export-unavailable" and row["verdict"] == "not-run"
            continue
        assert row["query_sha256"] == sha(corpus / attempt["query"])
        assert row["query_sha256"] == sha(output / "inputs" / (row["query"] + ".json"))
        directory = output / f"{row['query']}.{row['method']}.0"
        classified, expired, usage = classifier.classify_bounded_worker(
            directory, row["worker_exit_code"], row["outer_timeout"], row["usage"],
            row["wall_seconds"], 60, 2048 * 1024**2)
        assert all(row.get(key) == value for key, value in classified.items())
        assert row["outer_timeout"] == expired and row["usage"] == usage
        if row["verdict"] in {"reachable", "unreachable"}:
            assert row["independent_check"] and row["worker_exit_code"] == row["solver_exit_code"] == 0
            assert not expired and not usage["memory_limit_exceeded"]
            assert json.loads((directory / "solver.stdout").read_text())["verdict"] == row["verdict"]
    assert all(len(values & {"reachable", "unreachable"}) <= 1 for values in verdicts.values())
    evidence = [output / name for name in ("runs.jsonl", "environment.json", "sources.json")]
    evidence += list(output.glob("*/result.json")) + list(output.glob("*/solver.stdout"))
    report = dict(status="passed", rows=24, source_slots=12,
                  coverage={method: dict(Counter(row["status"] for row in rows if row["method"] == method)) for method in methods},
                  unresolved=sorted(name for name, values in verdicts.items() if values == {"unknown"}),
                  unavailable=sorted(name for name, values in verdicts.items() if values == {"not-run"}),
                  artifact_sha256={str(path.relative_to(ROOT)): sha(path) for path in evidence},
                  scope="Saved independent-check reconciliation using the frozen harness limit classification; no proof rerun. Local one-repeat development evidence, no competitor or stable timing claim.")
    save(ROOT / "research/transfer-raw-pilot-v1-verification.json", report)
    print(json.dumps({key: value for key, value in report.items() if key != "artifact_sha256"}, indent=2))


if __name__ == "__main__":
    main()
