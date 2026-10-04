# Reachability benchmark comparison

656 original properties; 5.0s budget; 1 repetition(s).

| Method | Reachable | Unreachable | Unknown | Errors/unsupported/unstable |
|---|---:|---:|---:|---:|
| native-walk | 405 | 227 | 8 | 16 |
| native-batched | 389 | 226 | 25 | 16 |
| native-frozen | 390 | 224 | 26 | 16 |
| verifypn-default | 376 | 227 | 37 | 16 |
| smpt-full-portable | 290 | 104 | 246 | 16 |

Collection coverage: {'planned': 656, 'imported': 640, 'unsupported': 16, 'explicitly_unobserved': 16}. Unsupported collection slots were not executed by any solver and remain in the denominator.
Bounded validation: {'enabled': True, 'seconds': 60.0, 'memory_mib': 2048, 'response_mib': 64, 'dag_check_max_work': 200000000, 'included_in_solver_timing': False}. Validation resource failures do not establish a definitive answer.
Reachability refers to EF targets or AG counterexamples; `property_truth` in runs.jsonl preserves the original property polarity.
Suite and family membership are preserved in the input manifest. No external verdict is treated as an oracle.
Definitive disagreements: [].
Native witnesses and available certificates are checked independently; per-branch verification status is recorded. External SMPT and VerifyPN proofs are not independently checked. Timings are exploratory on a shared host.

Dependency/interface failures were observed: {'smpt-full-portable': 3}. These runs do not establish a fully working configuration; inspect capability_failures in runs.jsonl.
