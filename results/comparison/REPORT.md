# Initial backend comparison

218 exported queries; medians of repeated cold-process runs.

| Method | Reachable | Unreachable | Unknown | Error/unstable |
|---|---:|---:|---:|---:|
| portfolio | 13 | 189 | 16 | 0 |
| smpt | 12 | 197 | 9 | 0 |

Definitive verdict disagreements: 0.

All queries: 218 queries, 201 solved by both. Native median speedup over SMPT on commonly solved queries: 17.89x; geometric mean: 19.32x.

Excluding syntactically false targets: 135 queries, 118 solved by both. Native median speedup over SMPT on commonly solved queries: 16.65x; geometric mean: 17.80x.

Solved only by portfolio: g4_disjunct_0.

Solved only by smpt: d1_disjunct_0, d3_disjunct_1, d4_disjunct_0, d4_disjunct_1, d4_disjunct_2, d4_disjunct_3, e1_disjunct_0, e7_disjunct_0.

These are backend-only measurements, including process startup and input parsing. SMPT uses the artifact configuration (STATE-EQUATION + BMC) and exports proofs. Native search replays witnesses; state-equation results carry exact Farkas certificates. An independent Python checker verifies those artifacts outside the timed backend run. Finite-state exhaustion results do not yet export an independently checkable certificate.

The collection attempted all 47 source benchmarks with a 20-second SMPT limit and 40-second frontend limit. It preserves queries emitted before a counterexample, timeout, or completion. It is not an exhaustive export of every disjunct, and these results do not establish an end-to-end serializability speedup.

The first scratch run in results/initial used polling-based process waits and is retained for diagnostics only. Use results/comparison for reported timings.
