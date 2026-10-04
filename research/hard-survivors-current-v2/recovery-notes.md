# Historical survivor comparison: interrupted audit and prepared recovery

The original experiment is **incomplete: 27/40 committed rows**. The unchanged full auditor rejects it. The new wrapper verifies that the retained rows form precisely the first 27 cells of the frozen schedule; their artifact/command/resource consistency audit passes. All 105 retained files match the fetched archive byte for byte. No artifacts for uncommitted cells were found. The original output, plan and terminal receipts remain untouched.

All 27 retained verdicts are Unknown: 13 timed out and 14 encountered cgroup OOM termination. Native-batched and native-frozen have six rows each; native-walk, VerifyPN and SMPT have five each. All five SMPT rows encountered OOM termination. There are no definitive answers or proof responses to revalidate. The audit retains 28 warnings, including missing/interrupted instruction counters. No claim about all eight queries or competitor superiority follows.

`interrupted-full-auditor-report.json` contains the unchanged auditor's failed full-matrix report. `interrupted-audit.json` separates that incompleteness from the available-row audit and preserves full rows, identities, warnings and the schedule. The initial wrapper's overly specific incompleteness-message mismatch is retained in `initial-interrupted-audit.*`; the final wrapper recognizes the observed missing-matrix diagnostic without removing other failures.

The exact 13 missing cells are:

| Original sequence | Query | Configuration |
|---|---|---|
| 28–30 | pigeonhole_p13_h12 | native-walk, SMPT full portable, VerifyPN |
| 31–35 | pigeonhole_p11_h10 | native-frozen, native-walk, SMPT full portable, VerifyPN, native-batched |
| 36–40 | ff_random_walk_double_lock_p2_vs_satabs_2_multi_100_0_c52c1204 | native-walk, SMPT full portable, VerifyPN, native-batched, native-frozen |

`recovery-plan.json` prepares these cells in that order, one invocation and fresh directory per cell. It retains the original corpus, native/competitor binaries, runner closure, engine flags, 300-second budget, CPU 8, 2 GiB, perf, two-million logical-work cap, zero outer grace, and separate 60-second native checking. Exact filters select one original property. SMPT proof paths change with output directories; preflight/startup is repeated outside recorded per-cell timing. Original 620/69/8 parent denominators remain. Recovery is deferred behind the new 176-query cohort.

The prepared `recovery-driver.py` is unexecuted. `recovery-service-command.json` and `.txt` contain a systemd user service launch command bound to the recovery-plan hash. The service owns the driver independently of SSH, requires user lingering, disables automatic restart, writes logs to disk, and uses an `ExecStopPost` receipt with a unique service invocation ID. The driver checks registered bytes and idle workloads, rejects existing outputs/receipts, and stops for inspection on a malformed or failed cell. It writes progress and a terminal receipt. The service's three-hour ceiling bounds the whole recovery; measured cell limits remain unchanged. The script received syntax and static command checks only; disconnect behavior is not empirically tested.

Before deployment or explicit launch, inspect authoritative host/process/unit state and all newer measurements, verify the original binary/source pins and MiniZinc preflight, and confirm user lingering. Do not replace changed shared scripts automatically to satisfy old pins. A reboot may prevent terminal receipts; missing receipts are not terminal evidence. Any driver failure requires checking sibling benchmark units before collection or retry.

After recovery, audit each output with its actual filter, method and output directory, then join by `(query, method, repeat)` against the original schedule. Preserve the original 27 rows and every new output/receipt as separate evidence. Label the combined result as measurements collected in two periods; do not claim equivalence to an uninterrupted run or stable timing. Missing cells remain unmeasured until committed and audited. No deployment, remote access, solver or benchmark was performed for this preparation.
