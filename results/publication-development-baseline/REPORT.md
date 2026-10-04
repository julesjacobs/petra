# Reachability benchmark comparison

256 original properties; 5.0s budget; 1 repetition(s).

| Method | Reachable | Unreachable | Unknown | Errors/unsupported/unstable |
|---|---:|---:|---:|---:|
| portfolio-v2 | 69 | 110 | 77 | 0 |
| smpt-full | 67 | 138 | 50 | 1 |

Reachability refers to EF targets or AG counterexamples; `property_truth` in runs.jsonl preserves the original property polarity.
Suite and family membership are preserved in the input manifest. No external verdict is treated as an oracle.
Definitive disagreements: [].
Native witnesses and available certificates are checked independently; per-branch verification status is recorded. SMPT proofs are not independently checked. Timings are exploratory on a shared host.
