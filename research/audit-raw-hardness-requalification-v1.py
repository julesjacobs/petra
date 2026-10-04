"""Reconcile saved raw requalification artifacts; do not rerun solvers/checkers."""
import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "research/raw-hardness-requalification-v1-plan.json"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


spec = importlib.util.spec_from_file_location("raw_registration", ROOT / "research/raw-hardness-requalification-v1-launch.py")
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)
plan = json.loads(PLAN.read_text())
hashes = {str(PLAN.relative_to(ROOT)): sha(PLAN)}
summaries = []
observations = defaultdict(list)
total_rows = 0
for run in plan["runs"]:
    launcher.verify_result(plan, run)
    output = ROOT / run["output"]
    rows = [json.loads(line) for line in (output / "runs.jsonl").read_text().splitlines()]
    for path in [output / "runs.jsonl", output / "environment.json", output / "sources.json"]:
        hashes[str(path.relative_to(ROOT))] = sha(path)
    for row in rows:
        observations[row["query"]].append(row["verdict"])
        if row["verdict"] == "not-run":
            continue
        directory = output / f"{row['query']}.{row['method']}.{row['repeat']}"
        result_path = directory / "result.json"
        if result_path.exists():
            result = json.loads(result_path.read_text())
            assert all(row.get(k) == v for k, v in result.items()), result_path
            hashes[str(result_path.relative_to(ROOT))] = sha(result_path)
        if row["verdict"] in {"reachable", "unreachable"}:
            expected = "verified-positive" if row["verdict"] == "reachable" else "verified-negative"
            assert row["status"] == expected and row["independent_check"]
            answer_path = directory / "solver.stdout"
            answer = json.loads(answer_path.read_text())
            assert answer["verdict"] == row["verdict"]
            hashes[str(answer_path.relative_to(ROOT))] = sha(answer_path)
    total_rows += len(rows)
    summaries.append(dict(cohort=run["cohort"], configuration=run["configuration"],
                          rows=len(rows), verdicts=dict(Counter(r["verdict"] for r in rows)),
                          statuses=dict(Counter(r["status"] for r in rows))))

for name, verdicts in observations.items():
    assert len(set(verdicts) & {"reachable", "unreachable"}) <= 1, name
assert total_rows == 112 and len(observations) == 24
report = dict(status="passed", rows=total_rows, unique_programs=24, summaries=summaries,
              unresolved=sorted(name for name, verdicts in observations.items() if set(verdicts) == {"unknown"}),
              export_unavailable=sorted(name for name, verdicts in observations.items() if set(verdicts) == {"not-run"}),
              stable_definitive=sorted(name for name, verdicts in observations.items() if len(set(verdicts)) == 1 and verdicts[0] in {"reachable", "unreachable"}),
              artifact_sha256=hashes,
              scope="Local 5s coverage qualification, two repetitions per frozen binary, checked native answers. Both binaries have identical raw solver modules. Reconciles saved checker responses; does not rerun proofs or establish source-to-query equivalence. No competitor comparison or stable speed claim.")
(ROOT / "research/raw-hardness-requalification-v1-analysis.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({k: v for k, v in report.items() if k != "artifact_sha256"}, indent=2))
