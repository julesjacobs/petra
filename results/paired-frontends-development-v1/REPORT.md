# Reachability benchmark comparison

256 original properties; 5.0s budget; 2 repetition(s).

| Method | Reachable | Unreachable | Unknown | Errors/unsupported/unstable |
|---|---:|---:|---:|---:|
| candidate-python | 100 | 156 | 0 | 0 |
| candidate-rust | 100 | 156 | 0 | 0 |
| verifypn-default | 95 | 156 | 5 | 0 |

Collection coverage: {'planned': 256, 'imported': 256, 'unsupported': 0, 'explicitly_unobserved': 0}. Unsupported collection slots were not executed by any solver and remain in the denominator.
Bounded validation: {'enabled': True, 'seconds': 30, 'memory_mib': 2048, 'response_mib': 1, 'included_in_solver_timing': False}. Validation resource failures do not establish a definitive answer.
Reachability refers to EF targets or AG counterexamples; `property_truth` in runs.jsonl preserves the original property polarity.
Suite and family membership are preserved in the input manifest. No external verdict is treated as an oracle.
Definitive disagreements: [].
Native witnesses and available certificates are checked independently; per-branch verification status is recorded. External SMPT and VerifyPN proofs are not independently checked. Timings are exploratory on a shared host.
