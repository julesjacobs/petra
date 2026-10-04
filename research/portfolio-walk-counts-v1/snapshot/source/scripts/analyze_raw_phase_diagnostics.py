#!/usr/bin/env python3
"""Summarize opt-in raw solver progress, retaining censored and truncated spans."""

import argparse
import json
import math
from pathlib import Path


def analyze(lines):
    phases = {}
    operations = {}
    issues = []
    ignored = 0
    records = 0
    truncated_pids = set()
    for line_number, line in enumerate(lines, 1):
        try:
            row = json.loads(line)
        except (ValueError, UnicodeError):
            if '"raw_phase_diagnostic"' in line:
                issues.append({"line": line_number, "issue": "malformed diagnostic record"})
            else:
                ignored += 1
            continue
        if not isinstance(row, dict) or "raw_phase_diagnostic" not in row:
            ignored += 1
            continue
        try:
            if row["raw_phase_diagnostic"] != "v1":
                raise ValueError("unsupported diagnostic version")
            for key in ["pid", "operation_id", "phase_id", "sequence", "charged_work"]:
                if type(row[key]) is not int or row[key] < 0:
                    raise ValueError(f"invalid {key}")
            for key in ["elapsed_seconds", "phase_seconds"]:
                value = row[key]
                if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                    raise ValueError(f"invalid {key}")
            for key in ["operation", "phase", "activity"]:
                if not isinstance(row[key], str):
                    raise ValueError(f"invalid {key}")
            if not isinstance(row["event"], str) or row["event"] not in {"phase-start", "phase-end", "progress", "activity-start", "diagnostics-truncated"}:
                raise ValueError("unknown event")
        except (KeyError, ValueError) as error:
            issues.append({"line": line_number, "issue": str(error)})
            continue

        records += 1
        op_key = (row["pid"], row["operation_id"])
        op = operations.setdefault(op_key, {"pid": op_key[0], "operation_id": op_key[1],
            "operation": row["operation"], "parent": row.get("parent"),
            "last_sequence": -1, "last_elapsed_seconds": 0, "diagnostics_truncated": False})
        if row["sequence"] != op["last_sequence"] + 1:
            issues.append({"line": line_number, "issue": "missing or reordered operation record"})
        if row["elapsed_seconds"] < op["last_elapsed_seconds"]:
            issues.append({"line": line_number, "issue": "decreasing elapsed time"})
        op["last_sequence"] = row["sequence"]
        op["last_elapsed_seconds"] = row["elapsed_seconds"]
        op["diagnostics_truncated"] |= row["event"] == "diagnostics-truncated"
        if row["event"] == "diagnostics-truncated":
            truncated_pids.add(row["pid"])

        key = (*op_key, row["phase_id"])
        phase = phases.setdefault(key, {"pid": key[0], "operation_id": key[1], "phase_id": key[2],
            "operation": row["operation"], "phase": row["phase"], "parent": row.get("parent"),
            "start_observed": False, "end_observed": False, "end_status": None,
            "first_record_line": line_number})
        if row["event"] == "phase-start":
            if phase["start_observed"]:
                issues.append({"line": line_number, "issue": "duplicate phase start"})
            phase["start_observed"] = True
        if row["event"] == "phase-end":
            if phase["end_observed"]:
                issues.append({"line": line_number, "issue": "duplicate phase end"})
            phase["end_observed"] = True
            phase["end_status"] = row.get("status")
        phase.update({"last_record_line": line_number, "last_observed_activity": row["activity"],
            "observed_phase_seconds": row["phase_seconds"],
            "operation_charged_work_at_last_record": row["charged_work"],
            "operation_counters_at_last_record": row.get("counters", {}),
            "operation_activity_nanoseconds_at_last_record": row.get("exclusive_activity_nanoseconds", {})})

    for key, phase in phases.items():
        phase["censored"] = not (phase["start_observed"] and phase["end_observed"])
        phase["operation_diagnostics_truncated"] = operations[key[:2]]["diagnostics_truncated"]
        phase["process_diagnostics_truncated"] = key[0] in truncated_pids
    for op in operations.values():
        op["process_diagnostics_truncated"] = op["pid"] in truncated_pids
    return {"format": "raw-phase-diagnostic-analysis-v1", "records": records,
        "ignored_lines": ignored, "issues": issues, "operations": list(operations.values()),
        "phases": list(phases.values()),
        "interpretation": "Unmatched phases are censored, including truncation. Last observed activity need not be the activity at death. Work/counters/activity times are cumulative within an operation; parent timings can include nested child work. Do not sum nested operations or treat missing phases as zero. This is diagnostic evidence, not a verdict or competitive timing."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stderr", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with args.stderr.open(errors="replace") as stream:
        result = analyze(stream)
    result["source"] = str(args.stderr)
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
