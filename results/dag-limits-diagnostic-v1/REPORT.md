# Reachability benchmark comparison

4 original properties; 5.0s budget; 1 repetition(s).

| Method | Reachable | Unreachable | Unknown | Errors/unsupported/unstable |
|---|---:|---:|---:|---:|
| dag-large | 0 | 0 | 1 | 3 |

Collection coverage: {'planned': 4, 'imported': 4, 'unsupported': 0, 'explicitly_unobserved': 0}. Unsupported collection slots were not executed by any solver and remain in the denominator.
Bounded validation: {'enabled': True, 'seconds': 30, 'memory_mib': 2048, 'response_mib': 1, 'included_in_solver_timing': False}. Validation resource failures do not establish a definitive answer.
Reachability refers to EF targets or AG counterexamples; `property_truth` in runs.jsonl preserves the original property polarity.
Suite and family membership are preserved in the input manifest. No external verdict is treated as an oracle.
Definitive disagreements: [].
Native witnesses and available certificates are checked independently; per-branch verification status is recorded. External SMPT and VerifyPN proofs are not independently checked. Timings are exploratory on a shared host.
