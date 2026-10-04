# Backend algorithm comparison

218 exported queries; medians of repeated cold-process runs.

| Method | Reachable | Unreachable | Unknown | Error/unstable |
|---|---:|---:|---:|---:|
| best-first | 3 | 16 | 199 | 0 |
| bfs | 14 | 16 | 188 | 0 |
| integer-state-equation | 0 | 195 | 23 | 0 |
| klm-schemes | 4 | 16 | 198 | 0 |
| marked-traps | 0 | 193 | 25 | 0 |
| portfolio | 13 | 197 | 8 | 0 |
| portfolio-old | 13 | 191 | 14 | 0 |
| smpt | 13 | 197 | 8 | 0 |
| state-equation | 0 | 191 | 27 | 0 |
| support | 0 | 0 | 218 | 0 |

Definitive verdict disagreements across all methods: 0.

Definitive verdict disagreements: 0.

All queries: 218 queries, 210 solved by both. Native median speedup over SMPT on commonly solved queries: 20.66x; geometric mean: 22.49x.

Excluding syntactically false targets: 135 queries, 127 solved by both. Native median speedup over SMPT on commonly solved queries: 19.64x; geometric mean: 22.21x.

Solved only by portfolio: none.

Solved only by smpt: none.

Other compiler workloads were active on the host; these wall timings are exploratory rather than isolated-machine measurements.

These are backend-only measurements, including process startup and input parsing. SMPT uses the artifact configuration (STATE-EQUATION + BMC) and exports proofs. Native search replays witnesses; arithmetic and structural refutations carry Farkas, integer-cut, marked-trap or empty-siphon certificates. An independent Python checker verifies those artifacts outside the timed backend run. Finite-state exhaustion does not export a certificate; the Python checker independently reconstructs finite closure up to 200,000 states. KReach uses a pure-VASS encoding of the target reduction, with conversion outside its timed process; its verdicts have no exported certificate.

The collection attempted all 47 source benchmarks with a 20-second SMPT limit and 40-second frontend limit. It preserves queries emitted before a counterexample, timeout, or completion. It is not an exhaustive export of every disjunct, and these results do not establish an end-to-end serializability speedup.

Each method receives the same solver time limit; a portfolio shares that limit among its stages. klm-schemes is bounded repeated-word search, not a complete KLMST implementation. The portfolio-old schedule uses the current improved rational engine; results/comparison preserves the original implementation measurements.
