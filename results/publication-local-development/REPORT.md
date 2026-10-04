# Reachability benchmark comparison

256 original properties; 5.0s budget; 2 repetition(s).

| Method | Reachable | Unreachable | Unknown | Errors/unsupported/unstable |
|---|---:|---:|---:|---:|
| relaxed-before | 100 | 155 | 1 | 0 |
| portfolio-local | 100 | 156 | 0 | 0 |
| verifypn-default | 95 | 156 | 5 | 0 |

Reachability refers to EF targets or AG counterexamples; `property_truth` in runs.jsonl preserves the original property polarity.
Suite and family membership are preserved in the input manifest. No external verdict is treated as an oracle.
Definitive disagreements: [].
Native witnesses and available certificates are checked independently; per-branch verification status is recorded. External SMPT and VerifyPN proofs are not independently checked. Timings are exploratory on a shared host.
