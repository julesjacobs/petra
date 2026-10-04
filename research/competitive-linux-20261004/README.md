# Four-tool Linux comparison: contended pilot

This campaign compares `portfolio-excess`, unrestricted VerifyPN defaults, qualified SMPT MCC portable scheduling and ITS-Tools MCC on the complete combined development cohort. The [protocol](protocol.json) fixes analysis and acceptance rules before measurement; [plan.json](plan.json) pins the runnable configurations. Both repetitions completed successfully, with all 2,944 invocations collected. See the [report](REPORT.md) for results and [handoff.json](handoff.json) for the original process identity. Do not restart this campaign.

**The idle-host launch objective was not met.** The saved one-minute host load averages were 34.37 and 25.06 on 32 logical CPUs at the two block starts. The preflight excluded competing workspace jobs but did not establish an idle host. All four tools were 1.41–1.82 times slower geometrically in the first block on their respective stable-solved subsets. These measurements are a contended development pilot; CPU affinity did not provide exclusive isolation, and an idle-host comparison remains outstanding.

| Method | Repeat 1 /368 | Repeat 2 /368 | Solved in both /368 |
|---|---:|---:|---:|
| Native `portfolio-excess` | 345 | 358 | 344 |
| VerifyPN unrestricted defaults | 298 | 299 | 298 |
| SMPT portable MCC | 205 | 238 | 202 |
| ITS-Tools MCC | 267 | 274 | 266 |

All 703 definitive native answers were independently checked. External answers remain tool-reported; no definitive answers disagree. Native gains/losses against VerifyPN reproduced in both blocks are 49/2. VerifyPN was 1.72 times faster on their 294 commonly solved properties, excluding native checking; this conditional timing result is affected by the host-load limitation.

The [original audit](audit.json) is preserved as failed: Z3 was omitted from the enforced dependency pins. Its identical binary identity was recorded before competitive launch through the execution → capability → qualification-environment hash chain and again in both blocks. The [amended audit](audit-v2.json) and its new analysis entry points preserve that limitation rather than rewriting the frozen plan. A saved-evidence consistency audit does not establish idle-host protocol conformance.

Two complete blocks use 368 original PNML/XML properties each, four methods, and seeds 2026100405 and 2026100406: **2,944 scheduled invocations**. Original-slot reporting retains all 368 properties; the ordered-branch representative view retains 366. The component cohorts remain visible: existing176 (175 representatives) and expansion192 (191 representatives). Reserved evaluation families are excluded.

Every property receives one strict five-second invocation on CPU 8 with enforced 2 GiB process-tree memory. Startup, query-specific staging/conversion and all branches share this budget. The native method uses two million states and buffer agglomeration. Native checking runs separately with 60 seconds, 2 GiB, a 64 MiB response bound and 200 million DAG work units. External answers remain tool-reported.

Each block shuffles the entire cohort and rotates methods per query; the second block reverses the base method order. Exact commands and schedules are frozen before launch. A failed external run that prints a definitive answer is recorded as unknown while preserving its reported answer, raw output and flags. Failed invocations remain in every denominator. An invalid accepted answer or definitive disagreement fails the audit.

The frozen launch protocol required frozen identities, qualified ITS runtime, the actual four-tool EF/AG capability harness passing its frozen acceptance rules, including the documented ITS timeout limitation, SMPT backend qualification and an idle host. No builds, tests, deployments or competing measurements were permitted to overlap a block. The workspace preflight did not establish the required host-wide idle condition. Partial or interrupted results remain available and are not replaced.

The saved-evidence audit checks pins, exact row matrix and order, terminal artifact hashes, original-input commands, deadlines, resource accounting, native validator evidence and cross-method/repeat consistency. It accepts retained failures as unknown while rejecting unsupported acceptance. It does not rerun solvers or proof checkers.

The report includes each repetition, both denominator views, both component cohorts, all twelve families, paired gains/losses, repeated solved sets, joint unresolved queries, solver PAR-2, actual solver and validation costs, and resource availability. Conditional timing ratios identify queries solved by both compared methods in both blocks. Native validation has no equivalent independent checking charge on external methods; that asymmetry remains explicit.

The current Mac result (363/368 twice) and earlier Linux candidate results are separate experiments. This campaign supplies a current comparison under recorded host contention; it does not establish idle-host performance, held-out generalization or novelty.

The original audit failure and frozen analysis sources are retained. The documented amended analysis uses fresh entry points:

```sh
python3 research/competitive-linux-20261004/audit-v2.py
python3 research/competitive-linux-20261004/summarize-v2.py
python3 research/competitive-linux-20261004/analysis-supplement-v2.py
```

These commands refuse to overwrite their output. The summarizer requires the amended audit and rechecks all audited artifact hashes. It never executes a solver or checker. The audit reuses the previous resource-sidecar parser and canonical-branch grouping, checks the new strict acceptance contract, and verifies its immutable analysis helpers and source inventory in `analysis-sha256.json`.

Linux release build and 621 tests passed (two ignored). The initial test compilation lacked three fixtures; the failed log and successful unchanged-source retry are retained. The actual 16-row four-tool harness and five SMPT component checks passed, with the documented ITS EF-2 timeout retained as unknown. ITS uses the verified official native image, with [qualification limitations](its-qualification/report.md).
