# Reachability benchmark comparison

218 original properties; 5.0s budget; 1 repetition(s).

| Method | Reachable | Unreachable | Unknown | Errors/unsupported/unstable |
|---|---:|---:|---:|---:|
| before | 175 | 0 | 43 | 0 |
| after | 174 | 0 | 44 | 0 |
| verifypn-default | 56 | 0 | 162 | 0 |
| smpt-full-portable | 30 | 0 | 188 | 0 |

Collection coverage: {'planned': 218, 'imported': 218, 'unsupported': 0, 'explicitly_unobserved': 0}. Unsupported collection slots were not executed by any solver and remain in the denominator.
Bounded validation: {'enabled': True, 'seconds': 30.0, 'memory_mib': 2048, 'response_mib': 1, 'dag_check_max_work': 20000000, 'included_in_solver_timing': False}. Validation resource failures do not establish a definitive answer.
Reachability refers to EF targets or AG counterexamples; `property_truth` in runs.jsonl preserves the original property polarity.
Suite and family membership are preserved in the input manifest. No external verdict is treated as an oracle.
Definitive disagreements: [].
Native witnesses and available certificates are checked independently; per-branch verification status is recorded. External SMPT and VerifyPN proofs are not independently checked. Timings are exploratory on a shared host.

Dependency/interface failures were observed: {'smpt-full-portable': 7}. These runs do not establish a fully working configuration; inspect capability_failures in runs.jsonl.
