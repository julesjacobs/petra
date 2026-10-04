# Target closure optimization screen

The old target-directed solver solved47/104; the optimized version solved46/104. One gain and two losses,45 common solves. Both proved16 negative answers. There is no net coverage improvement or stable timing result.

| Track | Queries | Old | Optimized |
|---|---:|---:|---:|
| MCC stress |50|30|30|
| FastForward |44|17|16|
| Synthetic |10|0|0|

The gain was FunctionPointer3 multi35. Losses were Dekker multi25 and lu_fig2 multi60. The conditional median optimized/old wall ratio was1.004 across45 common solves; unresolved cases are excluded and one repetition is insufficient for a speed claim.

All208 rows completed. All93 definitive native answers passed independent original-PNML/XML checking. All33 FastForward positive rows additionally passed original-LoLA replay. There were no errors, validation failures, disagreements or memory events; all115 unknowns hit the outer deadline. No exact ordered/canonical-branch duplicate groups were found in this104-query selection.

Both frozen binaries ran portfolio-target-stubborn at5seconds,one repeat,strict outer deadline,2GiB sampled Mac process-tree RSS and2million states. Parsing and preprocessing were timed;30s/2GiB/64MiB/20M-work independent validation was separate. Identities, limits, complete matrix and original input hashes were audited by audit-target-closure-screen-v1.py. This is outcome-selected development data from620 parent queries, with no held-out or external comparison claim.

The source change remains experimental. A19-query diagnostic (38rows) including every changed result is registered to inspect phase-specific limits, early full expansion and avoided repeated lists. A full104×2×3 repetition comparison is registered but unlaunched. No claim of stable improvement, regression, novelty or publication readiness follows.

Evidence: target-closure-screen-v1-{analysis,verification}.json, results/target-closure-screen-v1/{environment.json,runs.jsonl}, results/target-closure-screen-v1-lola-replay/report.json, and the frozen old/new artifacts solver-target-stubborn-v1 and solver-target-closure-v1.
