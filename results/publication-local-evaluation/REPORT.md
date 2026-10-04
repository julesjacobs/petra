# Reachability benchmark comparison

256 original properties; 5.0s budget; 2 repetition(s).

| Method | Reachable | Unreachable | Unknown | Errors/unsupported/unstable |
|---|---:|---:|---:|---:|
| frozen-v2 | 82 | 88 | 86 | 0 |
| portfolio-local | 114 | 137 | 5 | 0 |
| verifypn-default | 116 | 138 | 2 | 0 |

Reachability refers to EF targets or AG counterexamples; `property_truth` in runs.jsonl preserves the original property polarity.
Suite and family membership are preserved in the input manifest. No external verdict is treated as an oracle.
Definitive disagreements: [].
Native witnesses and available certificates are checked independently; per-branch verification status is recorded. External SMPT and VerifyPN proofs are not independently checked. Timings are exploratory on a shared host.
