# Reachability benchmark comparison

1 original properties; 5.0s budget; 1 repetition(s).

| Method | Reachable | Unreachable | Unknown | Errors/unsupported/unstable |
|---|---:|---:|---:|---:|
| bounded-token-cut | 0 | 0 | 1 | 0 |
| token-moment | 0 | 0 | 1 | 0 |
| projected-cegar | 0 | 0 | 1 | 0 |
| interval-invariant | 0 | 0 | 1 | 0 |
| causal-state-equation | 0 | 0 | 1 | 0 |

Reachability refers to EF targets or AG counterexamples; `property_truth` in runs.jsonl preserves the original property polarity.
Suite and family membership are preserved in the input manifest. No external verdict is treated as an oracle.
Definitive disagreements: [].
Native witnesses and available certificates are checked independently; per-branch verification status is recorded. External SMPT and VerifyPN proofs are not independently checked. Timings are exploratory on a shared host.
