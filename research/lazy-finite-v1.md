# Implicit-stutter comparison: complete results

The frozen lazy finite engine removes the explicit stutter-edge limit, but this
first comparison establishes no coverage gain.

| Comparison | Queries | Finite before | Finite after | Lazy | Focused |
|---|---:|---:|---:|---:|---:|
| Classical, 2 seconds | 37 | 20 | 20 | 20 | — |
| DLC7b RC01 probe, 20 seconds | 1 | — | 0 | 0 | 1 |
| Hard development, 2 seconds | 69 | — | 0 | 0 | 2 |

All 321 registered rows are present. All 63 definitive rows passed independent
checking; no reported errors or definitive disagreements occurred. Manifest,
frozen binary and archived runner hashes match the plans. Exact canonical-byte
deduplication leaves 34 classical representatives, with 19 solves for each method.

These are single-repeat macOS development measurements with sampled 2 GiB memory
limits, original PNML/XML inputs, and parsing/preprocessing included. Native
validation is separately bounded. They establish neither precise speedups nor
competitive superiority. Keep the 620-query parent denominator and reserved
families alongside the outcome-selected 69-query development view.

## What the DLC probe establishes

The explicit finite method produces no projection because of its edge limit.
The lazy method's raw branch diagnostics show six-mode projections with five
fixed edges and 333,012 implicit stutters, activating 42 or 106 columns. It reports
six pricing rounds, no cuts and no exact models before exhaustion. The measured
whole-property row remains **unknown / outer timeout** at 20 seconds; raw branch
diagnostics do not promote it to a validated answer. The focused portfolio returns
a reachable witness in 1.60 seconds, independently replayed.

Thus the representation passes the former graph-size barrier but has not solved
the query. Zero exact models alone does not distinguish numerical timeout,
solver failure or failed rational reconstruction.

## Regression qualification

Focused solves 2/69 here versus 3/69 in the earlier relevance screening. The lost
positive is `DLCflexbar-PT-7b__RC15`. These are different single-repeat runs under
a tight two-second deadline; treat this as requiring repeated qualification,
not as an established code regression. Do not substitute the earlier count.

## Next intervention

Eliminate final markings with m = m0 + Delta*x in the restricted numerical
master. Keep marking nonnegativity, substitute remaining rows, lift reduced
Farkas multipliers to the original canonical row indices, and recheck against
all implicit columns. Reconstruct and check original markings for primal models.
Preserve the objective too: each edge cost becomes 1 + sum of its place effects.
Recompute reductions when columns or cuts change. This has been reviewed
mathematically; implementation and performance validation remain pending.

The alternative of persistent microlp dual solves is less direct: each added
constraint reoptimizes and rebuilds the factorization, new cut variables require
a rebuild, and inherited per-edit time budgets need care. No performance claim
follows from API support alone.

Evidence: `lazy-finite-{classic,dlc-probe,hard}-v1-analysis.json`, corresponding
registered plans and raw result directories, and `lazy-finite-v1-verification.json`.
The separate 60-second Linux competition remains in progress.
