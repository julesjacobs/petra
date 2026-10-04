# Reachability benchmark comparison

176 original properties; 5.0s budget; 1 repetition(s).

| Method | Reachable | Unreachable | Unknown | Errors/unsupported/unstable |
|---|---:|---:|---:|---:|
| native-reduced | 89 | 46 | 41 | 0 |
| native-frozen | 83 | 45 | 48 | 0 |
| verifypn-default | 83 | 46 | 47 | 0 |
| smpt-mcc-portable | 51 | 43 | 82 | 0 |

Collection coverage: {'planned': 176, 'imported': 176, 'unsupported': 0, 'explicitly_unobserved': 0}. Unsupported collection slots were not executed by any solver and remain in the denominator.
Bounded validation: {'enabled': True, 'seconds': 60.0, 'memory_mib': 2048, 'response_mib': 64, 'dag_check_max_work': 200000000, 'included_in_solver_timing': False}. Validation resource failures do not establish a definitive answer.
Reachability refers to EF targets or AG counterexamples; `property_truth` in runs.jsonl preserves the original property polarity.
Suite and family membership are preserved in the input manifest. No external verdict is treated as an oracle.
Definitive disagreements: [].
Native witnesses and available certificates are checked independently; per-branch verification status is recorded. External SMPT and VerifyPN proofs are not independently checked. Timings are exploratory on a shared host.
