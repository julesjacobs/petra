# Backend algorithm comparison

218 exported queries; 2-second budget; 3 repetition(s), median cold-process wall times.

| Method | Reachable | Unreachable | Unknown | Error/unstable |
|---|---:|---:|---:|---:|
| portfolio | 14 | 197 | 7 | 0 |
| portfolio-next | 20 | 197 | 1 | 0 |
| smpt | 12 | 197 | 9 | 0 |

Definitive verdict disagreements across all methods: 0.

Definitive verdict disagreements: 0.

All queries: 218 queries, 209 solved by both. Native median speedup over SMPT on commonly solved queries: 17.57x; geometric mean: 18.43x.

Excluding syntactically false targets: 135 queries, 126 solved by both. Native median speedup over SMPT on commonly solved queries: 16.74x; geometric mean: 17.96x.

Solved only by portfolio: c5_disjunct_0, g4_disjunct_0.

Solved only by smpt: none.

portfolio-next versus portfolio: 211 commonly solved; median wall-time speedup 1.48x; geometric mean 1.40x.
Additional solves: c1_disjunct_0, e2_disjunct_0, e3_disjunct_2, e4_disjunct_2, g1_disjunct_0, g3_disjunct_1. Lost solves: none.

portfolio-next versus smpt: 209 commonly solved; median wall-time speedup 25.94x; geometric mean 26.06x.
Additional solves: c1_disjunct_0, c5_disjunct_0, e2_disjunct_0, e3_disjunct_2, e4_disjunct_2, g1_disjunct_0, g3_disjunct_1, g4_disjunct_0. Lost solves: none.

Native kosaraju implements complete generalized-VASS decomposition. This run imposes resource budgets, so unresolved cases return unknown. Negative Kosaraju results do not yet export independently checkable decomposition proofs.

Other compiler workloads were active on the host; these wall timings are exploratory rather than isolated-machine measurements.

These are backend-only measurements, including process startup and input parsing. SMPT uses the artifact configuration (STATE-EQUATION + BMC) and exports proofs. Native search replays witnesses; arithmetic and structural refutations carry Farkas, integer-cut, marked-trap or empty-siphon certificates. An independent Python checker verifies those artifacts outside the timed backend run. Finite-state exhaustion does not export a certificate; the Python checker independently reconstructs finite closure up to 200,000 states. KReach uses a pure-VASS encoding of the target reduction, with conversion outside its timed process; its verdicts have no exported certificate.

The collection attempted all 47 source benchmarks with a 20-second SMPT limit and 40-second frontend limit. It preserves queries emitted before a counterexample, timeout, or completion. It is not an exhaustive export of every disjunct, and these results do not establish an end-to-end serializability speedup.

Each method receives the same solver time limit; a portfolio shares that limit among its stages. klm-schemes is bounded repeated-word search, not a complete KLMST implementation. The portfolio-old schedule uses the current improved rational engine; results/comparison preserves the original implementation measurements.
