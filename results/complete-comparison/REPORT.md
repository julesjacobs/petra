# Backend algorithm comparison

218 exported queries; 2-second budget; 1 repetition(s), median cold-process wall times.

| Method | Reachable | Unreachable | Unknown | Error/unstable |
|---|---:|---:|---:|---:|
| kosaraju | 0 | 186 | 32 | 0 |
| portfolio | 14 | 197 | 7 | 0 |

Definitive verdict disagreements across all methods: 0.

Native kosaraju implements complete generalized-VASS decomposition. This run imposes resource budgets, so unresolved cases return unknown. Negative Kosaraju results do not yet export independently checkable decomposition proofs.

Other compiler workloads were active on the host; these wall timings are exploratory rather than isolated-machine measurements.

These are backend-only measurements, including process startup and input parsing. SMPT uses the artifact configuration (STATE-EQUATION + BMC) and exports proofs. Native search replays witnesses; arithmetic and structural refutations carry Farkas, integer-cut, marked-trap or empty-siphon certificates. An independent Python checker verifies those artifacts outside the timed backend run. Finite-state exhaustion does not export a certificate; the Python checker independently reconstructs finite closure up to 200,000 states. KReach uses a pure-VASS encoding of the target reduction, with conversion outside its timed process; its verdicts have no exported certificate.

The collection attempted all 47 source benchmarks with a 20-second SMPT limit and 40-second frontend limit. It preserves queries emitted before a counterexample, timeout, or completion. It is not an exhaustive export of every disjunct, and these results do not establish an end-to-end serializability speedup.

Each method receives the same solver time limit; a portfolio shares that limit among its stages. klm-schemes is bounded repeated-word search, not a complete KLMST implementation. The portfolio-old schedule uses the current improved rational engine; results/comparison preserves the original implementation measurements.
