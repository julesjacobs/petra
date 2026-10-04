"""Register and run seven local diagnostic cases, with existing bounded checking."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from analyze_raw_phase_diagnostics import analyze
from process_runner import workspace_workloads


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    binary = ROOT / "results/solver-raw-phase-diagnostics-v2/vass-reach"
    provenance = json.loads(binary.with_name("provenance.json").read_text())
    assert sha(binary) == provenance["binary_sha256"]
    assert sha(binary.with_name("source.tar.gz")) == provenance["source_sha256"]
    assert not workspace_workloads(ROOT)
    cases = ["write_skew_n3_pairlocked", "write_skew_n4_pairlocked", "write_skew_n5_pairlocked"]
    runs = []
    for label, selected, corpus in [("pairlocked", cases, "benchmarks/raw-diverse-automaton-v1"),
                                    ("optimistic", [f"optimistic_v{n}_validated" for n in [17, 25, 33, 49]], "benchmarks/raw-diverse-scaling-automaton-v1")]:
        states = 20_000_000
        output = f"results/raw-phase-diagnostics-v3-{label}"
        assert not (ROOT / output).exists()
        command = ["vendor/venv/bin/python", "scripts/benchmark_stress_raw.py",
                   "--corpus", corpus, "--output", output,
                   "--binary", str(binary), "--methods", "raw-negative", "--seconds", "30",
                   "--memory-mib", "2048", "--repeat", "1", "--max-states", str(states)]
        for case in selected:
            command += ["--case", case]
        runs.append(dict(command=command, output=output, cases=selected, max_states=states))
    source_names = ["scripts/benchmark_stress_raw.py", "scripts/raw_stress_worker.py",
                    "scripts/raw_invariant_check.py", "scripts/raw_schema_check.py",
                    "scripts/raw_automaton_check.py", "scripts/process_runner.py", "scripts/raw_z3.py",
                    "scripts/analyze_raw_phase_diagnostics.py", "research/run-raw-phase-diagnostics-v3.py",
                    "results/solver-raw-phase-diagnostics-v2/provenance.json",
                    "results/solver-raw-phase-diagnostics-v2/source.tar.gz",
                    "benchmarks/raw-diverse-automaton-v1/collection.json",
                    "benchmarks/raw-diverse-automaton-v1/source-manifest.json",
                    "benchmarks/raw-diverse-scaling-automaton-v1/collection.json",
                    "benchmarks/raw-diverse-scaling-automaton-v1/source-manifest.json"]
    identities = {name: sha(ROOT / name) for name in source_names}
    plan = dict(scope="Local phase/cap diagnostic, not competitive timing; local source editing may overlap, but no builds or competing solver jobs. Same frozen candidate; direct raw-negative uses the full solver phase. Expanded max-states sets both solver discovery and independent verifier work to 2 billion: this is a joint solver/checker diagnostic intervention, not an isolated search ablation or default algorithm change.",
                runs=runs, binary_sha256=provenance["binary_sha256"],
                source_archive_sha256=provenance["source_sha256"],
                environment={"VASS_RAW_PHASE_DIAGNOSTICS": "1"}, file_sha256=identities,
                limits="30 seconds input/check-inclusive, 80% remaining to solver; sampled 2 GiB process-tree RSS; one local invocation at a time.")
    with (ROOT / "research/raw-phase-diagnostics-v3-plan.json").open("x") as stream:
        json.dump(plan, stream, indent=2)
        stream.write("\n")
    environment = dict(os.environ, VASS_RAW_PHASE_DIAGNOSTICS="1")
    environment.pop("VASS_RAW_NEGATIVE_DIAGNOSTICS", None)
    results = []
    for run in runs:
        for name, expected in identities.items():
            assert sha(ROOT / name) == expected, name
        assert sha(binary) == provenance["binary_sha256"]
        subprocess.run(run["command"], cwd=ROOT, env=environment, check=True)
        output = ROOT / run["output"]
        rows = [json.loads(line) for line in (output / "runs.jsonl").read_text().splitlines()]
        assert {r["query"] for r in rows} == set(run["cases"]) and len(rows) == len(run["cases"])
        for row in rows:
            stderr = output / f"{row['query']}.raw-negative.0/solver.stderr"
            if stderr.exists():
                with stderr.open(errors="replace") as stream:
                    phases = analyze(stream)
                phases["stderr_sha256"] = sha(stderr)
                phases["source"] = str(stderr.relative_to(ROOT))
                stderr.with_name("phase-analysis.json").write_text(json.dumps(phases, indent=2) + "\n")
                results.append(dict(output=run["output"], row=row, analysis=phases))
            else:
                results.append(dict(output=run["output"], row=row, analysis=None))
    (ROOT / "research/raw-phase-diagnostics-v3-analysis.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
