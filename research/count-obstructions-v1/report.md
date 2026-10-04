# Execution obstructions in the survivor count models

An independent Python checker validates the state equation and target constraints
of each exported integer model, then exhausts all execution orders within its
per-transition count bounds. The DoubleExponent models have 424, 503 and 253
firings, respectively, but their bounded execution graphs contain only 69, 69 and
70 states. No state in these graphs satisfies the target. The greedy 28-step
prefix ends in a marking where no original transition is enabled. These are
failures of the proposed count vectors, not proofs about the original properties.

The exhaustive exploration also records every enabled transition whose proposed
count is exhausted. For RC02 branches 0 and 1, this execution frontier consists
of t34 and t42, both with proposed count zero. For RC07 branch 0, it consists only
of t34, also with count zero. Consequently every target-reaching execution must
satisfy x[t34] + x[t42] >= 1 for either RC02 branch, or x[t34] >= 1 for RC07 branch 0.
These constraints exclude the initial models and retain every actual witness.

The argument is a first-exit argument: any target-reaching execution must leave
the fully explored bounded execution graph. Its first exit fires an enabled
transition t after using all v[t] permitted occurrences, hence its total count
x[t] is at least v[t]+1. For a general frontier F the necessary constraint is
the disjunction of x[t] >= v[t]+1 over t in F. A sum >= 1 is equivalent only when
all frontier bounds are zero. Exhaustion without a target is essential; neither
a single deadlocked trace nor interrupted exploration justifies this cut.

This suggests an optional native count planner that alternates integer models
with bounded execution closure and execution-frontier refinement. Zero-bound
frontiers admit one sparse linear cut; other frontiers require a disjunction
(or an explicitly weaker necessary inequality). A replayed prefix that reaches
the target is already a valid witness, even if it does not realize all counts.
An incomplete closure must return unknown or continue a sound witness search;
it must not emit a frontier constraint. Keep the existing portfolio frozen while
testing this separately. Novelty is unassessed: state-equation refinement and
increment constraints have prior art and need a precise comparison.

TokenRing's initial model has four firings and no enabled counted transition.
Its frontier contains 15 zero-count transitions; this overlaps the existing
support-refinement mechanism. DoubleExponent RC07 branch 1 yields no model;
this diagnostic makes no infeasibility claim. Its independent negative proof is
already recorded in the separate survivor sweep.

All five diagnostic processes completed within the external budget. audit.json
records binary/input/log identities and exact enumeration counts. The Rust source
snapshot was formatted after compilation (formatting only); the actual executable
is separately frozen and hashed. These diagnostics are excluded from benchmark
coverage and timing comparisons. No production solver behavior changed.
