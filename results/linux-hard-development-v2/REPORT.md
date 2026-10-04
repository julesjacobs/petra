# Reachability benchmark comparison

69 original properties; 60.0s budget; 1 repetition(s).

| Method | Reachable | Unreachable | Unknown | Errors/unsupported/unstable |
|---|---:|---:|---:|---:|
| native-focused | 46 | 2 | 21 | 0 |
| native-symbolic | 47 | 2 | 13 | 7 |
| verifypn-default | 30 | 2 | 37 | 0 |
| smpt-full-portable | 1 | 8 | 60 | 0 |

Collection coverage: {'planned': 69, 'imported': 69, 'unsupported': 0, 'explicitly_unobserved': 0}. Unsupported collection slots were not executed by any solver and remain in the denominator.
Bounded validation: {'enabled': True, 'seconds': 60.0, 'memory_mib': 2048, 'response_mib': 1, 'dag_check_max_work': 20000000, 'included_in_solver_timing': False}. Validation resource failures do not establish a definitive answer.
Reachability refers to EF targets or AG counterexamples; `property_truth` in runs.jsonl preserves the original property polarity.
Suite and family membership are preserved in the input manifest. No external verdict is treated as an oracle.
Definitive disagreements: [].
Native witnesses and available certificates are checked independently; per-branch verification status is recorded. External SMPT and VerifyPN proofs are not independently checked. Timings are exploratory on a shared host.
