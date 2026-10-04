# Frozen validator extension

Prepared runner-smpt-single-core-v3 from the immutable v2 runner. Only
scripts/benchmark.py changes: support finite-closure-v1 and share closure traversal
with the legacy exhaustive-search answer check. Solver commands, scheduling,
resource limits and competitor code remain byte-identical to v2.

The current root benchmark.py lacks two proof handlers present in v2. The new
snapshot therefore applies only the closure extension to v2, preserving both
signed-threshold-invariant-v1 and phase-pair-closure-v1 and all prior handlers.

Fifteen harness/identity/closure tests pass, including malformed bounds and a false
negative claim on a reachable target. The first copied test suite also included an
obsolete prelaunch assertion that the historical result directory must not exist;
it failed because that historical run has completed. Its source and failed log are
preserved. Removing that unrelated historical-plan test leaves the 15 relevant
runner tests, all passing. No solver or checker behavior was changed to fix it.

The actual frozen bounded worker independently rechecks the saved complete original
RefineWMG positive and CloudReconfiguration negative answers. Receipts and copied
answers are in original-proofs/. These are checker checks on saved answers, not new
solver measurements. Linux capability preflight is still required before deployment
is considered qualified.

Archive SHA256: 2d0188faa1fe6475d2299525951fe46037fcb1d588a6bac6c647e64af4ef45f1.
This snapshot is local only and does not alter the running Linux comparison.
