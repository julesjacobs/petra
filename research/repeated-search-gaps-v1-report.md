# Finite repeated firing: initial application diagnostic

The opt-in repeated-firing search solves CircadianClock RC12 at the strict
five-second deadline. Its 400,003-step original-net witness passes the unchanged
independent Python check. It uses 62 search states and takes 0.179 seconds in
this one local run; the same-binary focused control times out at 5.032 seconds.
The combined buffer/repeated configuration takes 0.176 seconds with the same
state count and witness length. These are observed timings, not stable speedups.

All twelve rows of the three-query factorial diagnostic are retained:

| Configuration | Solved / 3 |
|---|---:|
| Focused control | 0 |
| Buffer | 2 |
| Repeated firing | 1 |
| Buffer and repeated firing | 3 |

The two NoC properties still require buffer reduction in this diagnostic. All
six definitive rows have saved successful independent witness checks. Four outer
timeouts are preserved. This is an outcome-selected development cohort, not
held-out or competitor evidence, and it does not establish full-set coverage.

The registered plan, frozen candidate, complete matrix, exact method/flag
assignments, file identities, budgets and saved positive validation records pass
`audit-repeated-search-gaps-v1.py`. This evidence audit reruns neither solvers nor
proof checkers. The candidate is in `results/solver-repeated-search-v1`, with
170 source files including patched varisat. The process session 90329 terminated
with exit code zero.

The follow-up is a full 192-query comparison with buffer reduction enabled for
both configurations, changing only focused search to repeated-firing search.
No default promotion follows from the three-query diagnostic.
