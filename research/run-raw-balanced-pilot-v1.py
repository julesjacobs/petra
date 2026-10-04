"""Register and run a matched local pilot; no remote operations."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from analyze_raw_phase_diagnostics import analyze
from process_runner import workspace_workloads


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


binary = ROOT / "results/solver-raw-balanced-v1/vass-reach"
provenance = json.loads(binary.with_name("provenance.json").read_text())
assert sha(binary) == provenance["binary_sha256"]
assert sha(binary.with_name("source.tar.gz")) == provenance["source_sha256"]
assert not workspace_workloads(ROOT)
cases = ["write_skew_n3_racy", "write_skew_n3_pairlocked",
         "write_skew_n5_racy", "write_skew_n5_pairlocked"]
runs = []
for tier, states in [("matched", 100_000_000)]:
    output = f"results/raw-balanced-pilot-v1-{tier}"
    assert not (ROOT / output).exists()
    command = ["vendor/venv/bin/python", "scripts/benchmark_stress_raw.py",
               "--corpus", "benchmarks/raw-diverse-automaton-v1", "--output", output,
               "--binary", str(binary), "--methods", "raw-portfolio", "raw-portfolio-balanced",
               "--seconds", "60", "--memory-mib", "2048", "--repeat", "1", "--max-states", str(states)]
    for case in cases:
        command += ["--case", case]
    runs.append(dict(output=output, command=command, max_states=states))
names = ["scripts/benchmark_stress_raw.py", "scripts/raw_stress_worker.py", "scripts/raw_invariant_check.py",
         "scripts/raw_schema_check.py", "scripts/raw_automaton_check.py", "scripts/raw_z3.py",
         "scripts/process_runner.py", "scripts/analyze_raw_phase_diagnostics.py",
         "research/run-raw-balanced-pilot-v1.py", "results/solver-raw-balanced-v1/provenance.json",
         "benchmarks/raw-diverse-automaton-v1/collection.json", "benchmarks/raw-diverse-automaton-v1/source-manifest.json"]
identities = {name: sha(ROOT / name) for name in names}
plan = dict(scope="Local matched scheduling pilot: same frozen solver/inputs/checker, legacy portfolio versus opt-in positive warmup and three-quarter negative phase.60s/2GiB; max_states100M yields10Bnegative-work/checker limit, with positive search state limits per stage. Whole-query wall/memory limits apply across stages. No novelty, competitive timing or global10Baggregate-work claim. No Linux operations.",
            cases=cases, rows=8, runs=runs, binary_sha256=provenance["binary_sha256"],
            source_archive_sha256=provenance["source_sha256"], file_sha256=identities,
            environment={"VASS_RAW_PHASE_DIAGNOSTICS": "1"},
            limits="60s input/check-inclusive; 80% remaining to solver; sampled2GiB tree RSS; one invocation at a time.")
with (ROOT / "research/raw-balanced-pilot-v1-plan.json").open("x") as stream:
    json.dump(plan, stream, indent=2)
    stream.write("\n")
environment = dict(os.environ, VASS_RAW_PHASE_DIAGNOSTICS="1")
environment.pop("VASS_RAW_NEGATIVE_DIAGNOSTICS", None)
combined = []
artifacts = {}
verdicts = defaultdict(set)
coverage = []
for run in runs:
    assert all(sha(ROOT / name) == digest for name, digest in identities.items())
    assert sha(binary) == provenance["binary_sha256"]
    subprocess.run(run["command"], cwd=ROOT, env=environment, check=True)
    output = ROOT / run["output"]
    rows = [json.loads(line) for line in (output / "runs.jsonl").read_text().splitlines()]
    assert len(rows) == 8 and {(r["query"], r["method"]) for r in rows} == {(q, m) for q in cases for m in ["raw-portfolio", "raw-portfolio-balanced"]}
    environment_record = json.loads((output / "environment.json").read_text())
    assert environment_record["binary_sha256"] == sha(output / "vass-reach") == provenance["binary_sha256"]
    for name, digest in environment_record["runner_sha256"].items():
        assert sha(output / "runner-source" / name) == digest == identities["scripts/" + name]
    for name in ("runs.jsonl", "environment.json", "sources.json"):
        artifacts[str((output / name).relative_to(ROOT))] = sha(output / name)
    for row in rows:
        assert row["repeat"] == 0
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
            verdicts[row["query"]].add(row["verdict"])
        stderr = output / f"{row['query']}.{row['method']}.0/solver.stderr"
        with stderr.open(errors="replace") as stream:
            phases = analyze(stream)
        phases["source_sha256"] = sha(stderr)
        stderr.with_name("phase-analysis.json").write_text(json.dumps(phases, indent=2) + "\n")
        combined.append(dict(tier=run["output"], row=row, phases=phases))
    for method in environment_record["methods"]:
        selected = [row for row in rows if row["method"] == method]
        coverage.append(dict(tier=run["output"], method=method, rows=len(selected),
                             statuses=dict(Counter(row["status"] for row in selected))))
(ROOT / "research/raw-balanced-pilot-v1-analysis.json").write_text(json.dumps(combined, indent=2) + "\n")
assert all(len(values) <= 1 for values in verdicts.values()), "Verdict disagreement"
report = dict(status="passed", rows=len(combined), coverage=coverage,
              checked_definitive_rows=sum(item["row"]["status"] in ("verified-negative", "verified-positive") for item in combined),
              artifact_sha256=artifacts,
              scope="Reconciles saved independent-checker results and frozen input/runner/binary identities; does not rerun proofs. Local diagnostic coverage only.")
(ROOT / "research/raw-balanced-pilot-v1-verification.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({key: value for key, value in report.items() if key != "artifact_sha256"}, indent=2))
