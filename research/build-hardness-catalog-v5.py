"""Extend the preserved v4 development catalog from completed, hash-checked evidence."""

from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {}
VERIFIED = {}


def digest(name):
    path = ROOT / name
    assert path.is_relative_to(ROOT) and "reserved" not in path.parts, name
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify(hashes):
    for name, expected in hashes.items():
        if name not in VERIFIED:
            VERIFIED[name] = digest(name)
        assert VERIFIED[name] == expected, f"Evidence hash changed: {name}"


def read(name):
    SOURCES[name] = digest(name)
    return json.loads((ROOT / name).read_text())


def audited(name):
    report = read(name)
    assert report["status"] == "passed", name
    verify(report.get("artifact_sha256", {}))
    return report


def main():
    result = read("benchmarks/development-hardness-catalog-v4.json")
    verify(result["source_sha256"])
    SOURCES.update(result["source_sha256"])
    SOURCES["research/build-hardness-catalog-v5.py"] = digest("research/build-hardness-catalog-v5.py")
    application = audited("research/application-ladder-qualification-v1/stage-300-audit.json")
    assert not application["audit_issues"] and application["rows"] == 16
    assert application["classification"]["validity"] == "complete_consistent_screen"
    survivors = application["classification"]["selections"]["all_unresolved"]
    assert len(survivors) == 4
    assert all(n == 0 for n in application["classification"]["full"]["definitive_by_method"].values())
    receipt = read("research/application-ladder-qualification-v1/stage-300-completion-receipt.json")
    assert receipt["terminal"] and receipt["exit_code"] == 0
    verify({str(Path(receipt["output"]) / name): value for name, value in receipt["sha256"].items()})
    collection_check = audited("research/transfer-raw-collection-v2-verification.json")
    collection_name = "benchmarks/raw-transfer-automaton-v2/collection.json"
    verify({collection_name: collection_check["collection_sha256"]})
    collection = read(collection_name)
    transfer_manifest = "benchmarks/transfer-ser-programs-v2/manifest.json"
    transfer = read(transfer_manifest)
    verify({transfer_manifest: collection["source_manifest_sha256"]})
    verify({str(Path(transfer_manifest).parent / c["source"]): c["sha256"] for c in transfer["cases"]})
    assert len(transfer["cases"]) == collection_check["source_slots"] == 12
    assert Counter(a["status"] for a in collection["attempts"]) == {"exported-unvalidated": 9, "timeout": 3}
    assert collection_check["export_statuses"] == {"exported-unvalidated": 9, "timeout": 3}
    pilot = audited("research/transfer-raw-pilot-v1-verification.json")
    phase = audited("research/transfer-raw-phase-v1-verification.json")
    storage = audited("research/raw-control-storage-v1-verification.json")
    compressed = audited("research/raw-compressed-cohorts-v1-verification.json")
    assert compressed["rows"] == 28 and compressed["unique_source_programs"] == 24
    assert compressed["unresolved"] == ["write_skew_n5_pairlocked"]
    assert compressed["unavailable"] == ["write_skew_n6_pairlocked"]
    assert sum(count for group in compressed["summaries"] for status, count in group["statuses"].items()
               if status in ("verified-positive", "verified-negative")) == 25
    assert pilot["rows"] == storage["rows"] == 24
    assert pilot["source_slots"] == storage["source_slots"] == 12
    assert len(pilot["unresolved"]) == len(pilot["unavailable"]) == phase["rows"] == 3
    assert all(c == {"memory-limit": 3, "verified-positive": 6, "export-unavailable": 3}
               for c in pilot["coverage"].values())
    assert {s["configuration"]: s["statuses"] for s in storage["summaries"]} == {
        "dense": {"memory-limit": 3, "verified-positive": 6, "export-unavailable": 3},
        "compressed": {"solver-timeout": 3, "verified-positive": 6, "export-unavailable": 3}}
    direct = audited("research/walk-gap-pilot-v1/verification.json")
    integrated = audited("research/walk-portfolio-gap-v1/verification.json")
    direct_plan = read("research/walk-gap-pilot-v1/plan.json")
    integrated_plan = read("research/walk-portfolio-gap-v1-plan.json")
    assert direct_plan["cases"] == integrated_plan["cases"]
    assert direct["queries"] == integrated["queries"] == len(direct_plan["cases"]) == 9
    assert direct["rows"] == 36 and direct["checked_definitive_rows"] == 27
    assert integrated["rows"] == 18 and integrated["checked_definitive_rows"] == 9
    assert direct["coverage"] == {"native-batched": {"unknown": 9}, **{
        f"native-walk-{seed}": {"reachable": 9} for seed in range(3)}}
    assert integrated["coverage"] == {"native-batched": {"unknown": 9}, "native-warm": {"reachable": 9}}
    assert not set(survivors) & set(direct_plan["cases"])

    result["format"] = "pvass-development-hardness-catalog-v5"
    result["supersedes"] = "benchmarks/development-hardness-catalog-v4.json"
    result["application_sixty_second_qualification"]["next"] = (
        "Completed300s qualification of all four joint survivors:16audited rows, no definitive answer. Original13/464parents and audit-role erratum preserved.")
    result["application_three_hundred_second_qualification"] = {
        "summary": application["classification"]["full"], "rows": 16,
        "joint_survivors": survivors, "warnings": len(application["warnings"]),
        "parent_denominators": {"initial_slots": 464, "initial_imports": 448,
                                "initial_exact_representatives": 442, "sixty_second_queries": 13},
        "limits": {"seconds": 300, "memory_bytes": 2147483648, "repeat": 1},
        "finding": "Four outcome-selected joint survivors of the tested configurations. Memory/resource failures and missing counters retained; not algorithm-independent hardness. Walk gap pilots cover different queries."}
    result["ordinary_tracks"][0]["next"] = "All13qualified at60s; all four joint survivors qualified at300s with no definitive answer. Preserve both complete stages and464-slot parent."
    result["ordinary_tracks"].append({
        "name": "application-ladder-five-minute-survivors",
        "manifest": "research/application-ladder-qualification-v1/stage-300/manifest.json",
        "parent_denominators": [464, 13, 4], "queries": survivors, "seconds": 300,
        "next": "Diagnose resource failures and evaluate general mechanisms; retain all16rows and28warnings."})
    result["transfer_family"] = {
        "source_manifest": transfer_manifest, "source_slots": 12, "exported_queries": 9,
        "export_timeouts": 3, "export_limits": collection["limits"],
        "pilot_rows": 24, "pilot_coverage": pilot["coverage"],
        "current_unresolved": pilot["unresolved"], "unavailable": pilot["unavailable"],
        "limits": {"seconds": 60, "memory_mib": 2048, "repeat": 1,
                   "negative_checker_work_per_stage": 10000000000},
        "phase_diagnostic": {"rows": phase["rows"], "observations": phase["observations"],
                             "finding": "Three memory failures during structural component-game expansion; counters are last observed, not final sizes. Schema queue exhaustion is not a completeness claim."},
        "compressed_control_comparison": {
            "rows": storage["rows"], "summaries": storage["summaries"],
            "coverage_gain": 0,
            "finding": "Both configurations check six early-release queries. All three available strict queries remain Unknown: dense memory limits become compressed solver timeouts. Preserve three unavailable exports per configuration."},
        "status": "Three current native-solver stress cases: n4path/cycle/chorded strict locking. Source arguments are not accepted backend proofs. Six unsafe witnesses independently checked; no competitor advantage or intrinsic hardness established. V1 twelve syntax failures preserved.",
        "next": "Develop and independently check a general negative-proof mechanism; retain full12-source parent and both strict/early-release variants."}
    result["selected_walk_gap_experiments"] = {
        "queries": direct_plan["cases"], "parent_slots": 656, "parent_imports": 640,
        "direct": {k: direct[k] for k in ("rows", "coverage", "checked_definitive_rows", "scope")},
        "integrated": {k: integrated[k] for k in ("rows", "coverage", "checked_definitive_rows", "scope")},
        "limits": {"solver_seconds": 5, "checker_seconds_separate": 60,
                   "memory_mib": 2048, "repeat": 1},
        "finding": "All nine selected positive gaps checked by each fixed walk seed and integrated warmup; matched batched0/9. These are distinct from the four300s joint survivors. No full-cohort regression, Linux timing, best-seed substitution or held-out claim."}
    result["raw_ser"]["current_classification"] = "Original diverse/scaling cohorts are a solved regression baseline at60s. New transfer family has three unresolved available strict queries; see transfer_family."
    result["raw_ser"]["compressed_control_regression"] = {
        "rows": 28, "checked_available_slots": 25, "available_slots": 27,
        "checked_available_unique_programs": 22, "available_unique_programs": 23,
        "summaries": compressed["summaries"], "unresolved": compressed["unresolved"],
        "finding": "Dense baseline retains27/27checked available slots. Compressed candidate loses n5pairlocked in both cohorts to solver-phase wall timeouts; no returned work-limit reason or phase trace. Keep candidate experimental; no pure storage ablation or stable timing claim."}
    result["raw_ser"]["next"] = "Retain27/27available original-cohort checks,28slots/24unique/four bridges/one export failure. Develop against the three transfer strict cases without removing their12-source parent or export failures."
    result["reservation"] = "All22reserved families remain excluded. This builder reads only named development evidence and its recorded artifacts; no reserved payloads or results read."
    result["source_sha256"] = dict(sorted(SOURCES.items()))
    result["verified_evidence_sha256"] = dict(sorted(VERIFIED.items()))
    result["hash_verification_scope"] = "Rehashed v4 source evidence, new passed audits' recorded artifacts,300s completion receipt, transfer collection and source bytes. Reconciles saved checks; does not rerun solvers, proofs, imports or measurements."
    output = ROOT / "benchmarks/development-hardness-catalog-v5.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"catalog": str(output), "source_files": len(SOURCES),
                      "verified_evidence_files": len(VERIFIED), "status": "passed"}))


if __name__ == "__main__":
    main()
