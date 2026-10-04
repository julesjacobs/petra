# Optimized candidate confirmation

Both complete repetitions and artifact audits passed. The candidate solves
363/368 properties in each; the baseline solves 323 and 322. There are 40 gains
reproduced in both runs and no losses. All 1,371 definitive answers passed
independent original-input checks. See [the full report](REPORT.md).

The final integrated candidate combines grouped-excess proofs with divided-marking and original guided witnesses before reductions, then divided-marking relaxed search and the prior fallbacks. The source passes 621 Rust tests (two ignored), Clippy, and the relevant independent checker tests before freeze. The previous grouped-only full audit is required and pinned. Execution status is recorded in plan, terminal and audit files; this protocol alone does not claim completion.

Run `run.py freeze --candidate /absolute/path/to/candidate`, then `run.py run repeat1`, `run.py audit repeat1`, `run.py run repeat2`, and `run.py audit repeat2` with `vendor/venv/bin/python`. Each stage contains 736 original-input invocations: all 368 slots against both binaries, strict five-second invocation budget, sampled 2 GiB, separate 60-second bounded independent validation.

Both corpora and every family remain visible; 366 exact ordered-branch representatives support the deduplicated view. Query order and method order are frozen, and corpus order reverses between repeats. The earlier grouped-only binary is a different candidate and its observations are not pooled as a repetition. Parent may run a separate preregistered RERS ablation; this full comparison never filters to a diagnostic subset.

For coverage, report both paired gains/losses, stable solved intersections and unions. Report actual solver and validation times separately and their sum for end-to-end cost. PAR-2 remains the solver-budget metric; do not silently add validator cost to a five-second penalty. Common-solved timing is conditional on both methods solving in both repeats. Two local repeats do not establish precise uncertainty or held-out generalization.

After both audits pass, `vendor/venv/bin/python research/grouped-excess-repeat-20261004/summarize.py` writes the paired repeat summary with original/representative denominators, intersections/unions, stable paired gains/losses, PAR-2, and solver-plus-validation totals and common-solved ratios. It refuses preexisting output and requires both pinned audits.
