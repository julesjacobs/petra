import json
import unittest

from analyze_raw_phase_diagnostics import analyze


def record(event="phase-start", sequence=0, operation=0, phase=0, **fields):
    row = {"raw_phase_diagnostic": "v1", "pid": 42, "operation_id": operation,
           "phase_id": phase, "operation": "negative", "phase": "game",
           "activity": "transfer", "sequence": sequence, "charged_work": sequence * 100,
           "elapsed_seconds": sequence / 10, "phase_seconds": sequence / 10,
           "event": event, "status": None, "parent": None}
    row.update(fields)
    return json.dumps(row)


class DiagnosticsTests(unittest.TestCase):
    def test_killed_child_and_parent_remain_separate_censored_phases(self):
        result = analyze([record(), record(operation=1, parent={"operation_id": 0, "phase_id": 0}),
                          record("progress", 1, operation=1)])
        self.assertFalse(result["issues"])
        self.assertEqual(len(result["operations"]), 2)
        self.assertTrue(all(phase["censored"] for phase in result["phases"]))
        self.assertEqual(result["phases"][1]["observed_phase_seconds"], 0.1)

    def test_complete_and_aborted_are_distinct_from_censored(self):
        result = analyze([record(), record("phase-end", 1, status="complete"),
                          record("phase-start", 2, phase=1),
                          record("phase-end", 3, phase=1, status="aborted")])
        self.assertEqual([p["end_status"] for p in result["phases"]], ["complete", "aborted"])
        self.assertTrue(all(not p["censored"] for p in result["phases"]))

    def test_truncation_does_not_finish_phase_even_with_complete_status(self):
        result = analyze([record(), record("diagnostics-truncated", 1, status="complete")])
        self.assertTrue(result["phases"][0]["censored"])
        self.assertTrue(result["operations"][0]["diagnostics_truncated"])

    def test_broken_last_line_is_reported_without_losing_progress(self):
        result = analyze(["old diagnostic text", record(), '{"raw_phase_diagnostic":'])
        self.assertEqual(result["records"], 1)
        self.assertEqual(result["ignored_lines"], 1)
        self.assertEqual(len(result["issues"]), 1)
        self.assertTrue(result["phases"][0]["censored"])

    def test_child_truncation_marks_parent_process_censored(self):
        result = analyze([record(), record(operation=1),
                          record("diagnostics-truncated", 1, operation=1)])
        parent = result["phases"][0]
        self.assertTrue(parent["process_diagnostics_truncated"])
        self.assertFalse(parent["operation_diagnostics_truncated"])
        self.assertTrue(parent["censored"])

    def test_gaps_and_invalid_times_are_reported(self):
        result = analyze([record(), record("progress", 3),
                          record("progress", 4, elapsed_seconds=float("nan"))])
        self.assertEqual(len(result["issues"]), 2)
        self.assertEqual(result["records"], 2)

    def test_invalid_event_type_and_missing_start(self):
        result = analyze([record(event=[]), record("phase-end", 1, status="complete")])
        self.assertEqual(len(result["issues"]), 2)
        self.assertTrue(result["phases"][0]["censored"])


if __name__ == "__main__":
    unittest.main()
