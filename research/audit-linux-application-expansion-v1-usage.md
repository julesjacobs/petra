# Application-expansion-v1 artifact audit

Wait until the Linux measurement process is independently confirmed terminal.
Then fetch the entire `results/linux-application-expansion-v1` directory, including
`runner-source`, solver outputs, validator requests/responses/logs, external logs,
systemd sidecars, raw perf files, and any exported proofs. A complete result matrix
does not establish process termination. This script neither fetches results nor
contacts Linux.

Run locally from the workspace root:

```sh
python3 research/audit-linux-application-expansion-v1.py
```

The default outputs are:

- `research/linux-application-expansion-v1-verification.json`: provenance,
  artifact hashes, every original row/failure, malformed-line evidence, resource
  checks, and the complete difficulty classification when available.
- `research/linux-application-expansion-v1-verification.md`: audit status and
  compact summary.

`--results PATH` selects a fetched directory under this workspace. `--output PATH`
changes the JSON destination; its `.md` sibling receives the summary. Output files
are replaced, so use a new output path when preserving an earlier audit.

Exit 0 means the saved evidence passes this consistency audit; it does not mean
all queries were solved. Exit 1 means missing, incomplete, conflicting, malformed,
or inconsistent evidence. Both exits save a report. Recorded failures remain in
the denominator; a harness exit status is never a reachability answer.

The audit checks:

- All registered file identities: local frozen input/native binary bytes, fetched
  runner snapshot bytes, and environment-reported remote tool/source hashes.
  Current development runners are not substituted for the frozen snapshot.
- The 192-query, 768-row matrix and registered scheduling, with 187 exact ordered
  branch-hash representatives, duplicate groups, and per-family denominators.
- Original-input commands, method configurations, CPU affinity, memory/time/state
  settings, and separately bounded validation settings.
- Saved native answers and validator requests/responses, external FORMULA output,
  capability failures, and systemd accounting consistency.
- Raw perf CSV fields against recorded counters, including runtime and coverage.
  Missing or partial counters after a recorded timeout/OOM with `perf_failure`
  remain warnings and are never filled with zero or imputed from partial data.
  Missing counters without that evidence fail the audit.

Classification reuses `scripts/analyze_application_expansion.py` unchanged.
Disagreements and invalid definitive answers make the artifact audit fail while
retaining the classification and all rows. An incomplete matrix has no completed
classification. This is a development difficulty screen with one repetition,
not held-out evaluation or stable performance evidence. Affinity is not exclusive
isolation; instruction counting does not remove timeout censorship or contention.

This audit does not rerun solvers, witnesses, or proof checkers. Native validation
is checked through saved independently checking worker responses; competitor
answers remain tool-reported. Remote binaries not fetched are identified only by
recorded hashes. Systemd sidecars record accounting rather than an independent
copy of configured limits; checking those limits relies on the frozen runner and
recorded settings. The script hashes additional captured artifacts but does not
claim that an artifact hash validates its proof contents.

Preparation tests:

```sh
python3 -m unittest discover -s scripts -p test_application_artifact_audit.py -v
```

Four test groups passed using temporary local files only. They cover a complete
synthetic 768-row/192-query/187-representative artifact set, missing sidecars,
empty/partial/duplicate/malformed matrices, null/missing environments, null and
partial perf counters, successful saved validation, null/partial/inconsistent
validator responses, conflicting external FORMULA output, and runner hash drift.
No completed application screen has been audited during this preparation.
