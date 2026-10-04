"""Index measured development gaps without merging incompatible denominators."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {}


def read(name):
    data = (ROOT / name).read_bytes()
    SOURCES[name] = hashlib.sha256(data).hexdigest()
    return json.loads(data)


def main():
    ladder = read("research/application-parameter-ladders-v2-screen-analysis.json")
    historical = read("research/linux-hard-survivors-v1-verification.json")
    raw = read("research/raw-component-game-portfolio-v1-analysis.json")
    requalified = read("research/raw-hardness-requalification-v1-analysis.json")
    assert requalified["status"] == "passed"
    requalified_v2 = read("research/raw-hardness-requalification-v2-analysis.json")
    balanced = read("research/raw-balanced-pilot-v1-verification.json")
    balanced_cohorts = read("research/raw-balanced-cohorts-v1-verification.json")
    assert balanced_cohorts["status"] == "passed" and balanced_cohorts["rows"] == 28
    assert balanced_cohorts["unique_source_programs"] == 24
    assert balanced_cohorts["unresolved"] == []
    assert balanced_cohorts["unavailable"] == ["write_skew_n6_pairlocked"]
    balanced_checked_slots = sum(count for cohort in balanced_cohorts["summaries"]
                                 for status, count in cohort["statuses"].items()
                                 if status in ("verified-positive", "verified-negative"))
    assert balanced_checked_slots == 27
    assert requalified_v2["status"] == balanced["status"] == "passed"
    assert requalified_v2["rows"] == 56 and balanced["rows"] == 8
    balanced_coverage = {
        item["method"]: {"rows": item["rows"], "statuses": item["statuses"],
                         "checked_definitive": sum(count for status, count in item["statuses"].items()
                                                   if status in ("verified-negative", "verified-positive"))}
        for item in balanced["coverage"]
    }
    assert balanced_coverage["raw-portfolio"]["checked_definitive"] == 1
    assert balanced_coverage["raw-portfolio-balanced"]["checked_definitive"] == 4
    diagnostic = read("research/raw-phase-diagnostics-v3-analysis.json")
    diagnostic_rows = [item["row"] for item in diagnostic]
    assert len(diagnostic_rows) == 7
    assert sum(row["status"] == "verified-negative" for row in diagnostic_rows) == 6
    assert [row["query"] for row in diagnostic_rows if row["status"] == "memory-limit"] == ["write_skew_n5_pairlocked"]
    pilot_verification = read("research/raw-adaptive-pilot-v1-verification.json")
    pilot = read("research/raw-adaptive-pilot-v1-analysis.json")
    comparison = read("research/linux-application-portfolio-comparison-v1-verification.json")
    assert comparison["status"] == "passed"
    application_60 = read("research/application-ladder-qualification-v1/stage-60-audit-v2.json")
    assert application_60["status"] == "passed"
    transfer = read("benchmarks/transfer-ser-programs-v2/manifest.json")
    followups = {name: read(f"research/{name}-verification.json") for name in (
        "raw-adaptive-groups-pilot-v1", "raw-control-sharing-pilot-v1",
        "raw-control-sharing-expanded-v1", "raw-proof-streaming-pilot-v1",
        "raw-checker-end-to-end-v1")}
    assert all(report["status"] == "passed" for report in followups.values())
    assert pilot_verification["status"] == "passed"
    assert len(pilot) == pilot_verification["rows"] == 16
    pilot_coverage = {}
    for item in pilot:
        key = item["tier"] + "/" + item["row"]["method"]
        counts = pilot_coverage.setdefault(key, {"rows": 0, "checked_definitive": 0})
        counts["rows"] += 1
        counts["checked_definitive"] += item["row"]["status"] in ("verified-negative", "verified-positive")
    assert ladder["validity"] == "complete_consistent_screen"
    assert historical["status"] == "passed"
    assert not historical["audit_issues"]

    ladder_manifest = "benchmarks/application-parameter-ladders-v2/manifest.json"
    historical_manifest = "benchmarks/hard-survivors-v1/manifest.json"
    ladder_queries = read(ladder_manifest)["queries"]
    historical_queries = read(historical_manifest)["queries"]
    assert len(ladder_queries) == ladder["properties"]
    assert set(historical["jointly_unresolved"]) <= {q["name"] for q in historical_queries}

    source_groups = []
    source_hashes = []
    for stem in ["diverse-ser-programs-v1", "diverse-ser-scaling-v1"]:
        name = f"benchmarks/{stem}/manifest.json"
        cases = read(name)["cases"]
        for case in cases:
            source = ROOT / "benchmarks" / stem / case["source"]
            assert hashlib.sha256(source.read_bytes()).hexdigest() == case["sha256"]
        source_hashes.extend(case["sha256"] for case in cases)
        source_groups.append({"manifest": name, "source_slots": len(cases),
                              "selection": "all sources, including export failures"})

    collection_groups = []
    for stem in ["raw-diverse-automaton-v1", "raw-diverse-scaling-automaton-v1"]:
        name = f"benchmarks/{stem}/collection.json"
        collection = read(name)
        collection_groups.append({"collection": name, "attempts": [
            {k: attempt[k] for k in ["name", "status", "source_sha256", "query"] if k in attempt}
            for attempt in collection["attempts"]
        ]})

    result = {
        "format": "pvass-development-hardness-catalog-v4",
        "scope": "Outcome-selected development views. Preserve full parents; no pooled score or held-out claim.",
        "completed_application_comparison": comparison["classification"]["full"],
        "application_sixty_second_qualification": {"summary": application_60["classification"]["full"], "joint_survivors": application_60["classification"]["selections"]["all_unresolved"], "next": "All four joint survivors registered at300s,16rows, running session81844; preserve the13/464parent denominators and audit-role erratum."},
        "transfer_family": {"source_manifest": "benchmarks/transfer-ser-programs-v2/manifest.json", "source_slots": len(transfer["cases"]), "status": "Frozen, eight finite-model tests passed, bounded raw export running session4823. All12 v1 attempts failed parsing and are preserved; v2 adds required no-op else branches. Difficulty unmeasured."},
        "ordinary_tracks": [
            {
                "name": "application-ladder-five-second-survivors",
                "manifest": ladder_manifest,
                "parent_slots": len(ladder_queries),
                "parent_imports": ladder["full"]["imported_properties"],
                "unavailable": ladder["selections"]["collection_unavailable"],
                "queries": ladder["selections"]["all_unresolved"],
                "seconds": 5,
                "next": "All13original queries qualified at60s: nine recovered by at least one method, four joint survivors now registered at300s. Keep original selection and failed rows.",
                "caveat": "Large input sizes and missing timeout phase data confound search hardness.",
            },
            {
                "name": "application-ladder-competitor-only",
                "manifest": ladder_manifest,
                "parent_slots": len(ladder_queries),
                "queries": [case["query"] for case in ladder["cases"] if case["competitor_only"]],
                "seconds": 5,
                "next": "Diagnose missed mechanisms; retain the full parent for regression comparisons.",
            },
            {
                "name": "historical-five-minute-survivors",
                "manifest": historical_manifest,
                "parent_denominators": [620, 69, 8],
                "queries": historical["jointly_unresolved"],
                "seconds": 300,
                "next": "Requalify all eight original queries with the current candidate and repaired SMPT before claiming current difficulty.",
                "caveat": "Historical configurations; memory limits and missing counters retained. Five FastForward random-walk cases and two synthetic pigeonhole cases remain unresolved.",
            },
        ],
        "raw_ser": {
            "current_classification": "regression/scaling baseline: every available current raw export independently checked at60s; no remaining unresolved search case at these limits",
            "current_unresolved": balanced_cohorts["unresolved"],
            "source_cohorts": source_groups,
            "source_slots": len(source_hashes),
            "unique_source_programs_by_byte_identity": len(set(source_hashes)),
            "duplicate_bridge_slots": len(source_hashes) - len(set(source_hashes)),
            "collections": collection_groups,
            "component_game_unresolved": raw["unresolved"],
            "five_second_requalification_unresolved": requalified["unresolved"],
            "five_second_requalification_rows": requalified["rows"],
            "five_second_requalification_export_unavailable": requalified["export_unavailable"],
            "diagnostic_followup": "Separate 30s direct-negative diagnostics with 2 billion solver/checker work prove six of seven queries, including n4 and validated optimistic v25/v33/v49. All six proofs are independently checked and finish below 2s locally. n5 exceeds sampled 2GiB. These are local diagnostic observations, not competitive timings or intrinsic-hardness claims.",
            "expanded_work_diagnostics": [{k: row[k] for k in ("query", "status", "wall_seconds", "query_sha256")} for row in diagnostic_rows],
            "adaptive_pilot": {
                "coverage": pilot_coverage,
                "checked_definitive_rows": pilot_verification["checked_definitive_rows"],
                "finding": "No coverage gain: both methods solve 2/4 at 20M work and 3/4 at 2B. n5 remains unresolved. Singleton projection introduced artificial growth; later bounded-group refinement also had no coverage gain.",
            },
            "subsequent_experiments": {name: {key: report[key] for key in ("rows", "coverage", "checked_definitive_rows")} for name, report in followups.items()},
            "latest_n5_status": "Independently accepted end-to-end at60s/2GiB/10Bwork after exact control sharing, typed streaming output and sparse duplicate-node keys. Local wall40.4s, sampled peak1776MiB. Same streaming binary with dense checker keys exceeds memory at the same limits. Historical30s failures remain unchanged. See research/raw-checker-sparse-identity-v1-report.md.",
            "sixty_second_requalification": {
                "status": requalified_v2["status"],
                "rows": requalified_v2["rows"],
                "unique_programs": requalified_v2["unique_programs"],
                "summaries": requalified_v2["summaries"],
                "unresolved": requalified_v2["unresolved"],
                "export_unavailable": requalified_v2["export_unavailable"],
                "finding": "Completed and audited56rows: direct negative checks13/28 source slots, legacy portfolio11/28; each includes one export failure. No positives survive the negative-first scheduling at these larger allowances. Work, resource and scheduling failures do not establish intrinsic hardness.",
            },
            "balanced_portfolio_pilot": {
                "status": balanced["status"],
                "rows": balanced["rows"],
                "coverage": balanced_coverage,
                "checked_definitive_rows": balanced["checked_definitive_rows"],
                "finding": "Same frozen binary/inputs/checker: balanced4/4 versus legacy1/4 at60s/2GiB, one repetition. Warmup checks both racy cases; longer negative slice checks n5. Local selected diagnostic; no stable timing or competition claim. No internal graph-memory cap.",
            },
            "balanced_full_cohort_qualification": {
                "status": balanced_cohorts["status"],
                "rows": balanced_cohorts["rows"],
                "checked_available_slots": balanced_checked_slots,
                "available_slots": balanced_cohorts["rows"] - len(balanced_cohorts["unavailable"]),
                "unique_source_programs": balanced_cohorts["unique_source_programs"],
                "available_unique_source_programs": balanced_cohorts["unique_source_programs"] - len(balanced_cohorts["unavailable"]),
                "summaries": balanced_cohorts["summaries"],
                "unavailable": balanced_cohorts["unavailable"],
                "finding": "Completed audited28slots: all27available independently checked (14reachable/13unreachable),24unique/23available programs, four bridge duplicates and one export failure retained. Local60s/2GiB one-repeat coverage; no competitor or stable timing claim.",
            },
            "next": "Retain the solved current raw cohorts as regression/scaling baselines and preserve historical failures. Twelve corrected transfer sources are frozen and raw export is running; no measured difficulty claim exists. Qualify all four ordinary application60s survivors at300s.",
            "caveat": "Raw automaton-Parikh exclusion differs from ordinary net properties; source expectations are not checked reachability answers.",
        },
        "reservation": "All 22 reserved families remain excluded. No reserved payloads or results read.",
        "source_sha256": SOURCES,
    }
    output = ROOT / "benchmarks/development-hardness-catalog-v4.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(output)


if __name__ == "__main__":
    main()
