"""Register, run and reconcile the full raw cohorts sequentially, locally."""
import hashlib
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


def main():
    prior = json.loads((ROOT / "research/raw-hardness-requalification-v2-plan.json").read_text())
    pilot = json.loads((ROOT / "research/raw-balanced-pilot-v1-verification.json").read_text())
    assert pilot["status"] == "passed" and pilot["rows"] == 8
    binary = ROOT / "results/solver-raw-balanced-v1/vass-reach"
    provenance = json.loads(binary.with_name("provenance.json").read_text())
    assert sha(binary) == provenance["binary_sha256"]
    assert sha(binary.with_name("source.tar.gz")) == provenance["source_sha256"]
    assert not workspace_workloads(ROOT)
    runs = []
    for cohort, info in prior["cohorts"].items():
        output = f"results/raw-balanced-cohorts-v1-{cohort}"
        assert not (ROOT / output).exists()
        command = [sys.executable, "scripts/benchmark_stress_raw.py", "--corpus", info["corpus"],
                   "--output", output, "--binary", str(binary), "--methods", "raw-portfolio-balanced",
                   "--all-sources", "--seconds", "60", "--memory-mib", "2048", "--repeat", "1",
                   "--solver-fraction", "0.8", "--max-states", "100000000"]
        runs.append(dict(cohort=cohort, output=output, command=command, sources=info["sources"]))
    names = {"scripts/" + name for name in json.loads(
        (ROOT / "results/raw-balanced-pilot-v1-matched/environment.json").read_text())["runner_sha256"]}
    names.update(["research/run-raw-balanced-cohorts-v1.py",
                  "research/raw-hardness-requalification-v2-plan.json",
                  "research/raw-balanced-pilot-v1-verification.json",
                  "results/solver-raw-balanced-v1/provenance.json"])
    for info in prior["cohorts"].values():
        names.update([info["corpus"] + "/collection.json", info["corpus"] + "/source-manifest.json"])
        for source in info["sources"]:
            if source["export_status"] == "exported-unvalidated":
                assert sha(ROOT / source["query"]) == source["query_sha256"]
                names.add(source["query"])
    pins = {name: sha(ROOT / name) for name in sorted(names)}
    denominators = dict(prior["denominators"], total_rows=28, expected_solver_invocations=27,
                        expected_not_run_rows=1)
    plan = dict(format="raw-balanced-cohorts-v1", runs=runs, denominators=denominators,
                limits=prior["limits"], binary_sha256=sha(binary),
                source_archive_sha256=provenance["source_sha256"], file_sha256=pins,
                scope="Full unchanged raw cohorts: 28 slots, 24 unique sources, four bridges and one export failure. One local invocation per slot, 60s input/check-inclusive, sampled 2GiB. Positive warmup then three-quarter negative slice then positive continuation. Per-stage work limits are not a global aggregate allowance. Independently check every accepted answer. No competitive timing or stability claim; reserved families untouched.")
    plan_path = ROOT / "research/raw-balanced-cohorts-v1-plan.json"
    with plan_path.open("x") as stream:
        json.dump(plan, stream, indent=2)
        stream.write("\n")
    environment = dict(os.environ)
    for name in ("VASS_RAW_PHASE_DIAGNOSTICS", "VASS_RAW_NEGATIVE_DIAGNOSTICS"):
        environment.pop(name, None)
    summaries, observations, artifacts = [], defaultdict(set), {str(plan_path.relative_to(ROOT)): sha(plan_path)}
    for run in runs:
        assert not workspace_workloads(ROOT)
        assert all(sha(ROOT / name) == digest for name, digest in pins.items())
        assert sha(binary) == plan["binary_sha256"]
        print("Starting " + run["output"], flush=True)
        subprocess.run(run["command"], cwd=ROOT, env=environment, check=True)
        output = ROOT / run["output"]
        rows = [json.loads(line) for line in (output / "runs.jsonl").read_text().splitlines()]
        sources = {source["name"]: source for source in run["sources"]}
        assert len(rows) == len(sources)
        assert {(r["query"], r["method"], r["repeat"]) for r in rows} == {
            (name, "raw-portfolio-balanced", 0) for name in sources}
        recorded = json.loads((output / "environment.json").read_text())
        assert recorded["binary_sha256"] == sha(output / "vass-reach") == plan["binary_sha256"]
        assert recorded["selected_sources"] == list(sources)
        for name, digest in recorded["runner_sha256"].items():
            assert sha(output / "runner-source" / name) == digest == pins["scripts/" + name]
        for name in ("runs.jsonl", "environment.json", "sources.json"):
            artifacts[str((output / name).relative_to(ROOT))] = sha(output / name)
        for row in rows:
            observations[row["query"]].add(row["verdict"])
            if sources[row["query"]]["export_status"] != "exported-unvalidated":
                assert row["status"] == "export-unavailable" and row["verdict"] == "not-run"
                continue
            assert row["query_sha256"] == sources[row["query"]]["query_sha256"]
            assert row["query_sha256"] == sha(output / "inputs" / (row["query"] + ".json"))
            directory = output / f"{row['query']}.{row['method']}.0"
            result_path = directory / "result.json"
            if result_path.exists():
                result = json.loads(result_path.read_text())
                assert all(row.get(key) == value for key, value in result.items())
                artifacts[str(result_path.relative_to(ROOT))] = sha(result_path)
            if row["verdict"] in ("reachable", "unreachable"):
                expected = "verified-positive" if row["verdict"] == "reachable" else "verified-negative"
                assert row["status"] == expected and row["independent_check"]
                assert row["worker_exit_code"] == row["solver_exit_code"] == 0
                assert not row["outer_timeout"] and not row["usage"]["memory_limit_exceeded"]
                answer = directory / "solver.stdout"
                assert json.loads(answer.read_text())["verdict"] == row["verdict"]
                artifacts[str(answer.relative_to(ROOT))] = sha(answer)
        summaries.append(dict(cohort=run["cohort"], rows=len(rows),
                              statuses=dict(Counter(row["status"] for row in rows))))
    assert sum(summary["rows"] for summary in summaries) == 28 and len(observations) == 24
    assert all(len(values & {"reachable", "unreachable"}) <= 1 for values in observations.values())
    report = dict(status="passed", rows=28, unique_source_programs=24, summaries=summaries,
                  unresolved=sorted(name for name, values in observations.items() if values == {"unknown"}),
                  unavailable=sorted(name for name, values in observations.items() if values == {"not-run"}),
                  artifact_sha256=artifacts,
                  scope="Reconciles saved independent checks and frozen artifacts; does not rerun proofs. Local coverage qualification, one repeat, no competitor timing claim.")
    (ROOT / "research/raw-balanced-cohorts-v1-verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "artifact_sha256"}, indent=2))


if __name__ == "__main__":
    main()
