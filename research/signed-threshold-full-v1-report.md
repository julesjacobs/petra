# Signed-threshold discovery: complete development screen

The completed local experiment passes the saved-artifact audit: 1,312 rows,
656 source slots, 640 imports and 16 unavailable slots for each configuration.
All 141 definitive rows passed independent original-input and certificate
checking. Native/threshold answers have no disagreements on common definitive
queries. The solver, runner, inputs and evidence hashes remain frozen.

| Standalone engine | Checked negatives / 640 | Unknown | Unavailable |
|---|---:|---:|---:|
| Binary signed-threshold | 100 | 540 | 16 |
| Unary signed-threshold | 41 | 599 | 16 |

Binary proves 61 properties unary does not; unary proves two binary does not.
Neither answers any of the eight remaining gaps from the strongest audited
native-walk Linux run (632/640). This is a capability comparison across hosts,
not a speed comparison or an executed integrated portfolio.

Binary's gains over unary span five families: CircadianClock, FMS, IOTPpurchase,
RwMutex and SmallOperatingSystem. Full query lists and family tables are in
`signed-threshold-full-v1-summary.json`.

## Costs and limits

For binary's 100 checked answers, median solver time is 0.050s and median
separate checker time is 0.148s. The corresponding totals are 10.328s and
274.646s; maximum checker time is 50.778s. Median checked end-to-end time is
0.218s. Unary's 41 checked answers have median solver/checker times
0.088s/0.760s. These populations differ; their medians are not paired speedups.
On the 39 jointly checked answers, median binary/unary solver ratio is 0.990
in this one local repetition.

Binary's TokenRing-40 RC04 candidate was downgraded to Unknown because independent
checking exceeded 60s; unary's answer checked successfully. The other unary-only
property is SharedMemory-50 RC04. There were no solver wall timeouts or sampled
solver memory failures. All failures and 16 collection failures remain recorded.

The frozen logical-work allowance of two million constrained this experiment:
687 unresolved binary branch attempts stopped at that cap, versus 188 reporting
bounded candidate discovery exhausted. Unary has 89 work-cap exits and 903
candidate-exhaustion exits. These are branch-attempt counts within Unknown
properties, not property denominators. All binary solver processes finished
within 1.120s, despite a 5s wall allowance. The experiment does not establish
that the candidate language is exhausted on the eight native gaps.

Keep the method opt-in. Before adding incremental evaluation or changing the
candidate language, diagnose the existing algorithm with a larger logical-work
allowance under the same hard wall budget. Any selected-gap diagnostic must
retain its full-cohort parents and precede a complete matched screen if it
motivates promotion. The preregistered new-family extension remains necessary;
this result alone does not support the method as the central contribution.

Evidence: `signed-threshold-full-v1-audit.json`,
`signed-threshold-full-v1-summary.json` and their reproducible scripts.
Single local repeat; sampled 2GiB; separate bounded checking; no stable speed,
general-superiority, novelty or publication-readiness claim.
