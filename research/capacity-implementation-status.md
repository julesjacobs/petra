# Checked capacity preprocessing: verified implementation

Source edits and local verification completed by portfolio_audit. All owned
Cargo, build, solver and validation handles are terminal. Root can schedule the
next measurement. No remote operations were performed.

- `src/capacity.rs`: target-directed NUPN ancestor supports and metadata-free
  single-input backward closures. Weighted original arc checks and initial
  mass certify every retained support. Malformed, cyclic, dangling or duplicate
  metadata disables hints. Checked supports export standard place-bound proofs.
- Target contradictions emit existing `sparse-farkas-v1` proofs, including signed
  coefficients and both equality orientations. Existing Rust verification runs
  before acceptance. A discovery result used with another net cannot bypass it.
- Focused/symbolic original-PNML pipelines share discovery across branches, using
  the source already read. Discovery receives 20% of the first branch budget,
  capped at 500ms and four million work units; fallback gets remaining time.
  `--no-capacity-preprocessing` provides a matched ablation. Existing methods and
  canonical query representations are preserved.
- Hint parsing is limited to 32MiB and 1.5 million XML nodes (also bounded by
  remaining work); XML bytes, parsed nodes, unit maps and arc scans consume work.
  XML parsing itself is not interruptible; the outer property deadline still
  governs acceptance.
- New tests: `tests/capacity.rs`, `tests/capacity_cli.rs`. Cover weighted forged
  safety claims, malformed unit graphs, signed/equality/extreme arithmetic,
  deadline/work exhaustion, changed-net verification, small concrete walks,
  and original-input CLI integration plus ablation.

Validation:

- Eight focused tests passed: `research/capacity-focused-tests.log`.
- Full Rust regression suite: 312 passed, zero failed, one pre-existing ignored:
  `research/capacity-full-tests.log`.
- Clippy with `--all-targets -- -D warnings` passed (existing vendored Varisat
  warnings remain): `research/capacity-clippy.log`.
- Locked release build passed: `research/capacity-release-build.log`.
- `results/capacity-functional-v1/report.json`: original-input functional probes
  for AutoFlight96b RC12, DLCflexbar7b RC03, DLCflexbar8b RC11. All three properties
  were refuted by checked capacity preprocessing, and all seven branch proofs
  passed bounded independent original-input translation and sparse Farkas
  checking. Five-second internal limits, eight-second outer functional limits;
  these are outcome-selected diagnostics, not a competitive timing experiment.

The later same-binary pilot reproduced all 14 predicted refutations in both
repetitions: `research/capacity-predicted-pilot-v1-verification.json`. Across the
complete 56-row matrix, capacity preprocessing solved all 14 selected properties
stably, compared with one stable solve when disabled. All 44 candidate branch
proofs passed independent checking; no validation failure was reported. These
are outcome-selected development cases and support a coverage gain on that
selection, not general superiority or isolated timing claims.

Full-family/full-corpus comparisons remain outstanding. The pilot uses the
frozen `solver-capacity-v1` artifact and predates the direct Rust sparse checker
change documented in `research/direct-farkas-checker.md`; that later change has
correctness evidence only. Capacities are exportable but are **not yet fed into
the token-flow engine**.
