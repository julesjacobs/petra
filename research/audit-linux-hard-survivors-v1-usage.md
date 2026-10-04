# Completed Linux survivor-run audit

After session 31070 is authoritatively terminal, fetch the entire result directory,
including `runner-source`, native answers, validator request/response files,
logs, systemd sidecars and raw perf files. Then run locally:

```sh
python3 research/audit-linux-hard-survivors-v1.py
```

Outputs:

- `research/linux-hard-survivors-v1-verification.json`: all original rows, failures,
  full 8/69/620 denominators, identity evidence, per-row resource/perf coverage,
  recorded answer/validator consistency, disagreements and audit issues.
- `research/linux-hard-survivors-v1-verification.md`: compact coverage summary and
  audit issues, with explicit limitations.

Exit 0 means the artifacts pass this consistency audit. It does not mean every
query was solved or independently prove competitor answers. Exit 1 means missing,
incomplete or inconsistent evidence; the report retains failures. The benchmark
harness itself may terminate with exit 1: inspect every retained row, never infer
an answer from that exit status. `error` and `unknown` never count as solved.
A complete matrix does not establish process termination; check termination first.

The script reads only local files and never invokes solvers, proof checkers,
benchmarks or network tools. It compares fetched frozen runner bytes rather than
current development scripts. Remote tool hashes are checked against recorded
`environment.json` metadata and explicitly labeled as such. Native binary and
input bytes are checked locally. It checks recorded independent-validator results
and saved answer consistency; it does not replay proofs or witnesses again.
Missing/multiplexed counters remain visible, including on failed runs.

Preparation checks passed for syntax, path normalization and perf coverage
classification. Two temporary incomplete-result smoke tests (empty directory and
three survivor rows with the actual previous environment schema) both saved failed
JSON/Markdown reports, retained all available rows, and exited 1 without crashing.
Temporary test directories were removed. The frozen external adapters accept
explicit FORMULA output before checking exit status: the audit therefore checks
that output and records nonzero external exits as warnings rather than assuming
that all successful competitor results require exit 0. The completed-run audit has not been run because the Linux
measurement is still active. No solver or Linux state was changed.
