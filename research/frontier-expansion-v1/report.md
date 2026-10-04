# Frontier-bound expansion: survivor probe

The optional frontier-count-plan-expanded method expands exhausted transition
bounds by min(2*v[t]+1, max_states), for up to three expansions per integer model.
It re-explores from the initial marking under the enlarged bounds. A complete
target-free graph still yields the exact first-exit disjunction; an interrupted
graph yields no constraint. Previously learned constraints remain in the integer
system. Only original-net-replayed witnesses are reported as definitive.

Expanded bounds need not satisfy the state equation. The first-exit argument needs
only nonnegative finite bounds and complete exploration. Tests cover arbitrary
small bounds, positive frontier thresholds, interrupted expansion, overflow, and a
read-arc example solved after two expansions without another integer query. Ten
unit tests, Clippy and the release build pass. Existing methods/defaults remain
available; the registered Linux candidate is unchanged.

All ten matched five-second branch runs pass artifact audit. Both the expanded
planner and frozen DFS planner return unknown on all five survivor branches.
Two invocations expire externally; no sampled memory limit is exceeded.

The expanded planner explores 1,011,931 and 1,026,307 states on the two DoubleExponent
RC02 branches, and 857,248 on RC07 branch 0. It reaches 125, 128 and 128 integer
models, respectively, with three expansions per model. These larger explorations
produce no new witness. TokenRing reaches its storage bound after 85,574 cumulative
states, one integer model and two expansions. RC07 branch 1 yields no integer model.

The complete development comparison in ../frontier-expansion-development-v1 confirms
no coverage change against frozen DFS. These results do not support promotion to
the main portfolio or increasing expansion depth. Further count-refinement changes
need a stronger algorithmic reason and comparison with existing CEGAR literature.

Plan SHA256: dbc853f611d3ead03fec583471cfa5d699cf4754ce0e0de05f1554443580e9b5.
Audit: audit.json, produced by ../audit-frontier-expansion-v1.py. This is a local
diagnostic, excluded from original-input competitor tables.
