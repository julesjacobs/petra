# Initial backend comparison

12 exported queries; medians of repeated cold-process runs.

| Method | Reachable | Unreachable | Unknown | Error/unstable |
|---|---:|---:|---:|---:|
| best-first | 0 | 0 | 12 | 0 |
| bfs | 3 | 0 | 9 | 0 |
| portfolio | 3 | 7 | 2 | 0 |
| state-equation | 0 | 7 | 5 | 0 |

These are backend-only measurements, including process startup and input parsing. SMPT uses the artifact configuration (STATE-EQUATION + BMC) and exports proofs. Native search replays witnesses; state-equation results carry exact Farkas certificates. An independent Python checker verifies those artifacts outside the timed backend run. Finite-state exhaustion results do not yet export an independently checkable certificate.

The collection attempted all 47 source benchmarks with a 20-second SMPT limit and 40-second frontend limit. It preserves queries emitted before a counterexample, timeout, or completion. It is not an exhaustive export of every disjunct, and these results do not establish an end-to-end serializability speedup.

The first scratch run in results/initial used polling-based process waits and is retained for diagnostics only. Use results/comparison for reported timings.
