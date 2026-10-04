# Raw phase diagnostic runner review

Read-only review of the analyzer/tests, diagnostic runner/freezer, and `RawQuery::from_json_file`/main call. Compared input-loading changes with the saved repeated-search source archive. Read the recorder event contract only to interpret analyzer fields; did not review changing solver instrumentation. No tests, builds, solvers or remote commands ran.

## Fix before relying on diagnostics

1. **Process-wide truncation is attributed only to the emitting operation.** `scripts/analyze_raw_phase_diagnostics.py:58,82` sets truncation only for the operation containing the marker. `src/raw_diagnostics.rs:208–222` implements a process-wide event cap. If a nested operation consumes the last slot, subsequent parent records are suppressed, but the parent gets `operation_diagnostics_truncated=false`. Keep the emitting-operation marker and add a process-level truncation flag inherited by all its operations/phases. A parent-start/child-start/child-truncation fixture should cover this case. Existing censoring correctly keeps the parent unfinished; the truncation attribution is the incorrect field.

2. **The input loader extends the raw JSON buffer lifetime even when diagnostics are disabled.** `src/raw_target.rs:78–83` binds `source` for the closure, retaining it through `validate()` and its temporary sets. Previously the `read_to_string` temporary was dropped at the parse statement before validation. This can increase peak memory and alter resource-limited outcomes on large queries. Add `drop(source)` immediately after successful deserialization, before entering the validation phase. The parsing and validation rules themselves are unchanged, and main still uses the original start time/deadline.

3. **The expanded-work intervention changes both solver and independent checker budgets.** `research/run-raw-phase-diagnostics-v1.py:28–35` increases `--max-states` from 200,000 to 2,000,000. `scripts/raw_stress_worker.py:235–236` derives checker work as `max_states * 100`, so the independent verification limit also grows from 20 million to 200 million. Register both limits explicitly and describe this as a joint intervention. Any eventual coverage gain must distinguish solver progress from newly affordable certificate checking. The current raw rows preserve `verification_work_limit` when verification starts, which supports that distinction.

4. **The claimed source-archive identity is copied without checking the archive.** `research/run-raw-phase-diagnostics-v1.py:48` records `provenance["source_sha256"]`, while only the binary is hashed at entry and before invocations. A missing or changed source archive therefore leaves an apparently valid registered source identity. Check the actual archive hash against provenance and include the provenance file and archive in the pinned identities. The freezer does verify archive contents against its own source manifest; this finding concerns the later runner.

## Additional limitations

- The freezer snapshots current source and copies the existing release binary. Its hashes establish the identities of both artifacts, but do not by themselves establish that the binary was built from that source. Preserve the actual build/test logs and ensure there were no source edits between the validated build and freeze. The `rustc -Vv` result is the compiler currently on PATH, not independently extracted build provenance.
- Analyzer schema handling can crash on a syntactically valid record with a list/object `event`: set membership raises `TypeError`, which is not caught. Validate the event type or catch `TypeError` if malformed-record tolerance is intended.
- `censored = not end_observed` only represents missing ends. A missing start followed by an observed end produces `censored=false` even though the interpretation says unmatched phases are censored. Retain separate start/end completeness or narrow that wording.
- The runner's environment is not fully pinned: dependencies/interpreter are recorded by the harness only partly, and inherited environment is retained. Suitable for a local diagnostic after explicit environment review; insufficient on its own for a portable reproducibility claim.

## Positive checks

The analyzer does not turn diagnostics into solver verdicts, retains malformed-line issues and observed progress, preserves unmatched phases, and warns against summing nested operation times. The runner retains all six registered invocations and original harness result rows. The existing bounded harness includes parsing and independent checking in the deadline and preserves non-definitive outcomes. No change to accepted input schema or raw target semantics was found in the reviewed loader/main diff. This is static evidence, not test execution or a soundness audit of the instrumentation.

## Static follow-up: fixes inspected

Re-read the current files after the root's edits. All four main findings are addressed: analyzer output adds `process_diagnostics_truncated` for every phase/operation sharing the marker PID; the loader explicitly drops `source` before validation; the runner states the joint 20M/200M discovery/checking intervention; and the runner checks and pins the actual source archive plus provenance. `solve_raw_negative` confirms the discovery multiplier is 100, matching the registered checker multiplier.

The analyzer also validates the event type and marks a phase censored if either its start or end is missing. Added fixtures cover nested process truncation, invalid event types, and missing starts; their source was inspected but tests were not executed. No remaining concrete blocker was found within the assigned scope. Build provenance and runtime-pinning limitations above remain limits on broader reproducibility claims.
