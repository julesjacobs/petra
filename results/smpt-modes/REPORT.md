# Published SMPT suites

37 original properties; 2s budget; 1 repetition(s).

| Method | Reachable | Unreachable | Unknown | Errors/unsupported/unstable |
|---|---:|---:|---:|---:|
| portfolio-next | 1 | 26 | 10 | 0 |
| smpt | 0 | 16 | 21 | 0 |
| smpt-induction | 0 | 1 | 36 | 0 |
| smpt-k-induction | 0 | 2 | 35 | 0 |
| smpt-pdr-cov | 0 | 0 | 37 | 0 |
| smpt-pdr-reach | 0 | 21 | 16 | 0 |
| smpt-pdr-saturated | 0 | 27 | 10 | 0 |
| smpt-portfolio | 0 | 35 | 2 | 0 |

Reachability refers to EF targets or AG counterexamples; `property_truth` in runs.jsonl preserves the original property polarity.
Certificate examples duplicate two expressiveness examples and are retained as a separate published suite. No external verdict is treated as an oracle.
Definitive disagreements: ['Performance__NTest__3u'].
Native witnesses and available certificates are checked independently; per-branch verification status is recorded. SMPT proofs are not independently checked. Timings are exploratory on a shared host.
