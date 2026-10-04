# Hard development screening: complete local results

The full 69-query comparison completed with 207 rows, one repetition per method,
two seconds per original PNML/XML property, and a sampled 2 GiB memory limit on
macOS. Parsing and preprocessing are included. Independent native validation is
outside solver timing. This is development screening, not competitive timing.

| Track | Queries | Finite before relevance | Finite with relevance | Focused portfolio |
|---|---:|---:|---:|---:|
| MCC application properties | 16 | 0 | 0 | 3 |
| Boolean consistency | 10 | 0 | 0 | 0 |
| FastForward random walk | 43 | 0 | 0 | 0 |
| Total | 69 | 0 | 0 | 3 |

The focused answers comprise one reachable and two unreachable properties. All
three passed independent checking. All other rows are unknown; there are no
reported errors or definitive disagreements. Unknown includes time/resource
limits and algorithmic inconclusiveness, and does not establish intrinsic hardness.
Manifest, frozen binaries and archived runner hashes match the registered plan.
The failed 18-row v1 run is preserved separately and contributes no rows here.

Backward relevance adds no finite-engine coverage in this comparison. Complete
finite-with-relevance outputs include 39 branch attempts that exhausted the edge
limit before producing any projection, and 24 branch attempts that reached six
projections but refuted none of a single terminal mode. These are branch counts,
not query counts; 13 rows had no complete JSON answer. The full distribution is
in `relevant-finite-hard-v2-verification.json`. Investigating constant-coordinate
selection and sound static support reduction is justified; their benefit remains
unverified.

The 69 queries are an outcome-selected development view of 620 parent queries,
with limited family diversity. Keep full parent comparisons and the eight reserved
MCC families for evaluating generalization. The classical 37-query suite remains
useful for regression checks but both full portfolios already solve it.

The separate 60-second Linux comparison with focused Rust, symbolic Rust,
VerifyPN and SMPT is still running. Do not select a 300-second qualification set
from partial results. First audit its complete matrix, preserve validation-limit
failures, and separately recheck oversized certificates under uniform registered
limits. Only then classify jointly unresolved queries and tool-specific gaps.

Machine-readable evidence: `relevant-finite-hard-v2-analysis.json` and
`relevant-finite-hard-v2-verification.json`. Registered plan:
`relevant-finite-hard-v2-plan.json`. Raw results:
`../results/relevant-finite-hard-v2/`.
