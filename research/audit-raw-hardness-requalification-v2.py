"""Reconcile saved raw requalification artifacts; do not rerun solvers/checkers."""
import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "research/raw-hardness-requalification-v2-plan.json"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


spec = importlib.util.spec_from_file_location("raw_registration", ROOT / "research/raw-hardness-requalification-v2-launch.py")
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)
plan = json.loads(PLAN.read_text())
hashes = {str(PLAN.relative_to(ROOT)): sha(PLAN)}
erratum_path = ROOT / 'research/raw-hardness-requalification-v2-registration-erratum.json'
erratum = json.loads(erratum_path.read_text())
assert erratum['plan_sha256'] == sha(PLAN)
hashes[str(erratum_path.relative_to(ROOT))] = sha(erratum_path)
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
                          rows=len(rows), by_method={method: dict(Counter(r["status"] for r in rows if r["method"] == method)) for method in plan["methods"]}, verdicts=dict(Counter(r["verdict"] for r in rows)),
                          statuses=dict(Counter(r["status"] for r in rows))))

for name, verdicts in observations.items():
    assert len(set(verdicts) & {"reachable", "unreachable"}) <= 1, name
assert total_rows == 56 and len(observations) == 24
report = dict(status="passed", rows=total_rows, unique_programs=24, summaries=summaries,
              registration_erratum=erratum,
              unresolved=sorted(name for name, verdicts in observations.items() if set(verdicts) == {"unknown"}),
              export_unavailable=sorted(name for name, verdicts in observations.items() if set(verdicts) == {"not-run"}),
              all_methods_definitive=sorted(name for name, verdicts in observations.items() if len(set(verdicts)) == 1 and verdicts[0] in {"reachable", "unreachable"}),
              artifact_sha256=hashes,
              scope="Local60s full-cohort coverage qualification, one repetition each for direct negative and portfolio, one frozen binary and sparse checker keys. Methods have different schedules; no repeated-run stability claim. Reconciles saved checker responses; does not rerun proofs or establish source-to-query equivalence. No competitor comparison or stable speed claim.")
(ROOT / "research/raw-hardness-requalification-v2-analysis.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({k: v for k, v in report.items() if k != "artifact_sha256"}, indent=2))
