# Signed-threshold kernel: verified foundation, no coverage result yet

Implemented a supplied-invariant kernel over unary/binary signed linear
threshold clauses, with exact BigInt arithmetic and sparse implication graphs.
The independent Python checker reconstructs its own graph and induction checks.
The Rust CLI accepts this proof kind through --verify. Every original transition
is checked, with a same-mode zero-update shortcut; reads keep their weighted
guards. Target equalities and signed affine forms are encoded exactly. Boolean
SAT is a rejected proof obligation, never a concrete witness.

242 Rust tests passed (225 library,4 original CLI,8 phase-pair,5 new cross-language
integration tests). New differential tests cover1800Boolean truth tables and
1000finite-net candidates in Rust,400Boolean truth tables and624finite-net checks
in Python. All15Python threshold tests passed. Formatting and project Clippy
passed; existing vendored varisat warnings remain. The malformed-input and
breaking-transition mutations are rejected by both implementations.

Phase-pair's independently reproduced unreferenced-target schema gap is repaired.
Seven Python schema/composition tests passed, including30malformed-field cases
and actual bounded original-input workers. Existing shared benchmark.py remains
pinned by the live Linux run. A new isolated runner v2 carries the repair and
phase-pair dispatch; historical v1 bytes remain unchanged and hash-verified.
See phase-pair-schema-v2/report.md for the precise scope and retained initial
fixture failures.

The kernel has no automatic invariant discovery or new benchmark coverage.
It has no trace monitor, cross-template arithmetic axioms, path certificate or
watched dependency optimization. Both checkers recompute graph contradictions.
The next implementation step is deterministic bounded full-rescan candidate
elimination, with unary ablation, before optimizing representation or scheduling.

The user's priority is coverage and speed first. Proof checking supports
correctness; proof representation alone is not the intended research result.
The completed Pro review and assessment are in pro-pair-review-v1. Its proposed
ten additional negatives over the strongest native configuration is infeasible
in the existing cohort with8Unknowns; a harder preregistered development
extension is needed for a broad research claim. All22reserved families remain
untouched, and the existing portfolio is unchanged.

Reproducible source archive and validation logs:
results/kernel-signed-threshold-v1 (no benchmark release binary).
Linux historical comparison session31728 remains active at latest poll. No
remote builds/imports/transfers until authoritative terminal completion.
