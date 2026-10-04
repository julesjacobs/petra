# Reachability benchmark comparison

3 original properties; 5.0s budget; 1 repetition(s).

| Method | Reachable | Unreachable | Unknown | Errors/unsupported/unstable |
|---|---:|---:|---:|---:|
| native-portfolio | 0 | 0 | 3 | 0 |
| native-focused | 0 | 0 | 3 | 0 |
| native-batched | 0 | 0 | 3 | 0 |
| native-target | 0 | 0 | 3 | 0 |

Collection coverage: {'planned': 3, 'imported': 3, 'unsupported': 0, 'explicitly_unobserved': 0}. Unsupported collection slots were not executed by any solver and remain in the denominator.
Bounded validation: {'enabled': True, 'seconds': 60.0, 'memory_mib': 2048, 'response_mib': 64, 'dag_check_max_work': 200000000, 'included_in_solver_timing': False}. Validation resource failures do not establish a definitive answer.
Reachability refers to EF targets or AG counterexamples; `property_truth` in runs.jsonl preserves the original property polarity.
Suite and family membership are preserved in the input manifest. No external verdict is treated as an oracle.
Definitive disagreements: [].
Native witnesses and available certificates are checked independently; per-branch verification status is recorded. External SMPT and VerifyPN proofs are not independently checked. Timings are exploratory on a shared host.
