# Target-guided enabled walks

Opt-in `walk-guided` uses the existing weighted enabled-transition index and
marking updates. For each place, a sparse reverse index lists target coefficients.
Each firing incrementally updates exact i128 target values; checked arithmetic
failure returns Unknown. Candidate deltas use the same reverse index.

On four out of five selection opportunities, sample eight enabled transitions
with replacement and minimize the sum of successor target violations; ties use
reservoir sampling. On the remaining opportunities choose uniformly. Equalities
use absolute distance; inequalities use positive deficit. Scoring converts exact
distances to f64 solely to rank proposals. Neither scores nor failed searches
justify an answer. Every positive requires original-net witness replay within
the caller's deadline. Existing restart, trace and total-firing caps remain.

`walk-incremental` uses the same target-value maintenance but exactly the uniform
selection/random stream. This separates target-evaluation cost from selection
policy. Original `walk` behavior and default portfolio schedules remain unchanged.
Three modes share the existing CLI seed and restart controls.

Correctness checks compare incremental values and every candidate score against
full weighted successor computations across resets, read arcs, consumption and
sources, including signed targets and i64::MIN. The incremental control must
match uniform traces/steps/markings under fixed seeds and firing caps. Search
limits, deadlocks and overflow remain Unknown. CLI tests cover both new modes.

Constants were fixed by the prior proposal before new outcomes. Initial matched
qualification will retain all eight native-walk Unknowns from the audited656-slot
Linux comparison, including both known negative TokenRing cases. This is an
outcome-selected development pilot, not broad effectiveness evidence. Positive
search may lose on negative or plateau-heavy cases. Full-parent evaluation and
seed sensitivity remain necessary before portfolio integration.
