# Reachability benchmark comparison

37 original properties; 2s budget; 3 repetition(s).

| Method | Reachable | Unreachable | Unknown | Errors/unsupported/unstable |
|---|---:|---:|---:|---:|
| portfolio-next | 1 | 26 | 10 | 0 |
| portfolio-v2 | 1 | 36 | 0 | 0 |
| smpt-portfolio-unsaturated | 0 | 28 | 9 | 0 |

Reachability refers to EF targets or AG counterexamples; `property_truth` in runs.jsonl preserves the original property polarity.
Suite and family membership are preserved in the input manifest. No external verdict is treated as an oracle.
Definitive disagreements: [].
Native witnesses and available certificates are checked independently; per-branch verification status is recorded. SMPT proofs are not independently checked. Timings are exploratory on a shared host.
