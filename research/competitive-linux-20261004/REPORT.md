# Current four-tool Linux comparison — contended pilot

**Host contention materially limits this pilot.** The recorded one-minute load averages were 34.37 and 25.06 on 32 logical CPUs. Each tool was 1.41–1.82 times slower in repeat 1 on its own common-solved queries. This is a contended pilot, not an idle-host measurement; CPU affinity and the workspace workload gate did not establish host-wide isolation. Timings and deadline-sensitive coverage should not be treated as an uncontended comparison. The provenance amendment does not repair the idle-host launch objective or certify idle-host protocol conformance.

**Provenance amendment:** The frozen audit failed because `vendor/venv/bin/z3` was omitted from its enforced pins. The saved pre-launch capability chain and both block environments record the same executable hash. [The amended audit](audit-v2.json) accepts only this documented omission; the [original failed audit](audit.json) remains unchanged. Matching observations do not establish continuous pin enforcement.

Contended five-second Linux pilot with two complete development repetitions and a documented provenance amendment. Native results independently checked; external answers tool-reported. No idle-host, held-out or novelty claim.

Each method receives one five-second original-property invocation on CPU 8 with enforced 2 GiB process-tree memory. All 2,944 invocations remain in the record. Native answers are independently checked; external answers are tool-reported.

| Method | Solved repeat 1 /368 | Solved repeat 2 /368 | Both /368 | Representatives repeat 1 /366 | Representatives repeat 2 /366 |
|---|---:|---:|---:|---:|---:|
| native-excess | 345 | 358 | 344 | 343 | 356 |
| verifypn-default | 298 | 299 | 298 | 297 | 298 |
| smpt-mcc-portable | 205 | 238 | 202 | 204 | 237 |
| its-mcc | 267 | 274 | 266 | 266 | 273 |

| Competitor | Candidate gains/losses, repeat 1 | Repeat 2 | Gains/losses in both |
|---|---:|---:|---:|
| verifypn-default | 51/4 | 61/2 | 49/2 |
| smpt-mcc-portable | 141/1 | 123/3 | 107/1 |
| its-mcc | 82/4 | 88/4 | 74/3 |

Pairs compare the candidate against each competitor in the same block. The summary retains exact queries and the representative view. Intersections and unions across repeats describe repeatability; they are not measured portfolios.

| Cohort | Slots | native-excess | verifypn-default | smpt-mcc-portable | its-mcc |
|---|---:|---:|---:|---:|---:|
| existing176 | 176 | 160 / 173 | 129 / 129 | 79 / 92 | 96 / 100 |
| expansion192 | 192 | 185 / 185 | 169 / 170 | 126 / 146 | 171 / 174 |
| ASLink | 32 | 26 / 26 | 16 / 17 | 15 / 24 | 29 / 28 |
| ClientsAndServers | 32 | 32 / 32 | 31 / 31 | 0 / 0 | 21 / 24 |
| CloudReconfiguration | 32 | 32 / 32 | 32 / 32 | 3 / 11 | 28 / 28 |
| DNAwalker | 32 | 32 / 32 | 17 / 17 | 12 / 15 | 11 / 12 |
| HouseConstruction | 32 | 32 / 32 | 32 / 32 | 32 / 32 | 29 / 29 |
| IBM319 | 16 | 16 / 16 | 16 / 16 | 16 / 16 | 12 / 13 |
| MAPK | 32 | 32 / 32 | 31 / 31 | 32 / 32 | 29 / 29 |
| NQueens | 32 | 32 / 32 | 32 / 32 | 27 / 32 | 32 / 32 |
| RERS17pb114 | 32 | 17 / 29 | 0 / 0 | 0 / 0 | 0 / 0 |
| Railroad | 32 | 31 / 31 | 27 / 27 | 20 / 26 | 31 / 32 |
| RefineWMG | 32 | 31 / 32 | 32 / 32 | 16 / 18 | 29 / 30 |
| TriangularGrid | 32 | 32 / 32 | 32 / 32 | 32 / 32 | 16 / 17 |

Entries show repeat 1 / repeat 2 solved counts. All properties and all twelve families remain represented.

| Method | Solver total | Validation total | Solver + recorded validation | Mean solver PAR-2 |
|---|---:|---:|---:|---:|
| native-excess | 577.528 s | 440.194 s | 1017.722 s | 1.012 s |
| verifypn-default | 844.772 s | 0.000 s | 844.772 s | 2.072 s |
| smpt-mcc-portable | 2206.315 s | 0.000 s | 2206.315 s | 5.058 s |
| its-mcc | 1191.664 s | 0.000 s | 1191.664 s | 2.960 s |

Totals cover both repetitions. PAR-2 charges every unsolved invocation ten seconds. External totals contain no equivalent independent proof-checking cost.

| Competitor | Common solved in both repeats | Competitor/candidate solver ratio | Ratio including recorded checking |
|---|---:|---:|---:|
| verifypn-default | 294 | 0.581 | 0.308 |
| smpt-mcc-portable | 200 | 6.390 | 3.389 |
| its-mcc | 261 | 1.705 | 0.854 |

Ratios are geometric means of per-query median ratios, conditioned on both methods solving in both repeats. Values above one favor the candidate on that selected subset. Checking remains asymmetric.

| Method | Failure flags repeat 1 | Failure flags repeat 2 |
|---|---|---|
| native-excess | nonzero_exit: 21, timeout: 21 | nonzero_exit: 7, timeout: 7 |
| verifypn-default | nonzero_exit: 70, timeout: 70 | nonzero_exit: 69, timeout: 69 |
| smpt-mcc-portable | capability_failure: 154, error: 129, nonzero_exit: 138, timeout: 139 | capability_failure: 126, error: 99, nonzero_exit: 103, timeout: 103 |
| its-mcc | capability_failure: 8, error: 101, nonzero_exit: 93, timeout: 93 | capability_failure: 7, error: 94, nonzero_exit: 93, timeout: 93 |

Failure flags overlap. Raw reported answers rejected after failure remain available. Unknown is not an unreachability answer.

Never solved by any method in either repeat: 6 original properties. Exact queries, per-query variation, admission failures and resource availability are in [summary.json](summary.json).

All new expansion arcs have unit weights; the corpus does not establish weighted-arc breadth. Development-family selection and earlier tuning limit generalization. Reserved evaluation families remain untouched. CPU affinity does not imply exclusive host isolation. Two repetitions do not establish precise timing uncertainty, novelty or general competitive superiority.

Plan SHA-256: `d230dcc763b15b09a08cc45d9e605513b1cfdbc7173d82dfcc6d1765ef867ec0`.
Candidate binary SHA-256: `107f2269fe12a147ffced9c44e4d7c91f3834705e927bb104a2fa8ec70eb7f9f`.
ITS runtime used: Official GraalVM native image with pinned product plugins and GreatSPN; product 1.0.0.202609112134. Unverified; native and product obtained from official paired installation URLs on 2026-10-04. Product SHA matches prior pin. Qualification attempts and their failures are separate from competitive rows.
ITS qualification retains documented timeout, unsupported-input and auxiliary-error limitations; those outcomes remain unknown in this comparison. Exact competitor/runtime/source identities and commands are in [plan.json](plan.json). The [protocol](protocol.json), [amended audit](audit-v2.json), [provenance amendment](analysis-amendment-v2.json), [analysis source hashes](analysis-v2-sha256.json), block terminal receipts and raw artifacts preserve all inputs, outcomes and checking evidence.
