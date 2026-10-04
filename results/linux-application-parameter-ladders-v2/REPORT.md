# Reachability benchmark comparison

464 original properties; 5.0s budget; 1 repetition(s).

| Method | Reachable | Unreachable | Unknown | Errors/unsupported/unstable |
|---|---:|---:|---:|---:|
| native-focused | 259 | 162 | 27 | 16 |
| native-symbolic | 259 | 162 | 27 | 16 |
| verifypn-default | 247 | 167 | 34 | 16 |
| smpt-full-portable | 197 | 72 | 179 | 16 |

Collection coverage: {'planned': 464, 'imported': 448, 'unsupported': 16, 'explicitly_unobserved': 16}. Unsupported collection slots were not executed by any solver and remain in the denominator.
Bounded validation: {'enabled': True, 'seconds': 60.0, 'memory_mib': 2048, 'response_mib': 64, 'dag_check_max_work': 200000000, 'included_in_solver_timing': False}. Validation resource failures do not establish a definitive answer.
Reachability refers to EF targets or AG counterexamples; `property_truth` in runs.jsonl preserves the original property polarity.
Suite and family membership are preserved in the input manifest. No external verdict is treated as an oracle.
Definitive disagreements: [].
Native witnesses and available certificates are checked independently; per-branch verification status is recorded. External SMPT and VerifyPN proofs are not independently checked. Timings are exploratory on a shared host.
