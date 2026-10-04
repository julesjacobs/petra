# Whole raw-query comparison

5 programs; 2s; 1 repetition(s).

| Method | Reachable | Unknown | Errors/unstable |
|---|---:|---:|---:|
| raw-bfs | 0 | 5 | 0 |
| raw-potential | 2 | 3 | 0 |
| raw-z3 | 0 | 5 | 0 |

Unknown includes all safe instances unless an engine implements a negative proof. A raw query has an entire semilinear-complement target; counts are not comparable to old per-disjunct coverage. raw-z3 is a new direct quantified BMC baseline, not SMPT. All positives are independently replayed and checked against each excluded linear set with Z3 outside timing.
