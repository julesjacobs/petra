# Whole raw-query comparison

24 programs; 2s; 1 repetition(s).

| Method | Reachable | Unknown | Errors/unstable |
|---|---:|---:|---:|
| raw-bfs | 10 | 14 | 0 |
| raw-search | 8 | 16 | 0 |
| raw-z3 | 3 | 21 | 0 |

Unknown includes all safe instances unless an engine implements a negative proof. A raw query has an entire semilinear-complement target; counts are not comparable to old per-disjunct coverage. raw-z3 is a new direct quantified BMC baseline, not SMPT. All positives are independently replayed and checked against each excluded linear set with Z3 outside timing.
