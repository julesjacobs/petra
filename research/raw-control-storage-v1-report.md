# Compressed control storage: no coverage gain

All24 registered rows completed. The saved verification passes; its39 artifact
hashes, frozen binaries/runners/inputs, classifications and terminal log were
rechecked. All12 definitive rows retain successful independent checks. This
reconciliation did not rerun proofs or measurements.

| Configuration | Checked reachable | Memory limit | Solver timeout | Export unavailable |
|---|---:|---:|---:|---:|
| Dense | 6 | 3 | 0 | 3 |
| Compressed | 6 | 0 | 3 | 3 |

Both solve the same six early-release queries:6/9 available exports, preserving
all12 source slots. The three n4 strict queries remain unknown. The three n6
strict export failures are unavailable inputs, not solver failures. No negative
proof or coverage gain was obtained; strict-locking source expectations remain
distinct from verified exported-net answers.

Compressed controls remain below sampled2GiB but reach the solver-phase deadline:

| Query | End-to-end wall | Sampled peak process-tree RSS |
|---|---:|---:|
| transfer_n4_path_strict | 48.21s | 971 MiB |
| transfer_n4_cycle_strict | 48.20s | 892 MiB |
| transfer_n4_chorded_strict | 48.36s | 1326 MiB |

Limits are60s input/check-inclusive outer wall,80% of remaining time for the
solver, sampled2GiB process-tree RSS,100M states/10B applicable negative-checker
work and one repeat. Both use balanced scheduling and the same checker. The
interning work charge changed from2d to8d, so this is **not a pure storage
ablation**; work counters are not instruction counts. The longer surviving runs
and lower observed memory do not establish greater search progress, stable speed,
intrinsic hardness or superiority over competitors.

Next diagnostic: after active experiments finish, register a phase-instrumented
n4 path-strict comparison with identical interning work charges and fixed
whole-query limits. Record completed schemas, distinct controls, game nodes,
OR targets, transfer/coefficient effort and each stage's stop reason. This will
separate encoding/hash overhead from graph growth and portfolio fallback time.
Before promoting compressed storage, rerun the previous full raw regression
cohort, including the checked n5 proof, retaining every source/export slot.
No diagnostic or regression was launched during this closeout.

Evidence: `raw-control-storage-v1-plan.json`,
`raw-control-storage-v1-verification.json`, `raw-control-storage-v1.log`, and the
dense/compressed result folders. Execution is now `complete-audited`.
