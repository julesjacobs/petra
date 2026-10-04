# Reachability benchmark comparison

5 original properties; 5.0s budget; 2 repetition(s).

| Method | Reachable | Unreachable | Unknown | Errors/unsupported/unstable |
|---|---:|---:|---:|---:|
| portfolio-causal | 0 | 0 | 5 | 0 |
| portfolio-v3 | 0 | 0 | 5 | 0 |
| sparse-count-plan | 3 | 0 | 2 | 0 |
| causal-state-equation | 0 | 0 | 5 | 0 |
| token-cut | 0 | 0 | 5 | 0 |
| bounded-token-cut | 0 | 0 | 5 | 0 |

Reachability refers to EF targets or AG counterexamples; `property_truth` in runs.jsonl preserves the original property polarity.
Suite and family membership are preserved in the input manifest. No external verdict is treated as an oracle.
Definitive disagreements: [].
Native witnesses and available certificates are checked independently; per-branch verification status is recorded. External SMPT and VerifyPN proofs are not independently checked. Timings are exploratory on a shared host.
