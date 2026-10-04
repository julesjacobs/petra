# Finite repeated-transition search

The opt-in `relaxed-batched` and `portfolio-batched` methods add finite repeated
firings to the existing positive search. Default methods retain their existing
successors. This is classical finite acceleration as an engineering improvement;
there is no novelty, completeness or performance claim at implementation time.

For input multiplicity a, output multiplicity b, effect d=b-a, marking m and
positive repeat count k, every prefix is enabled exactly when m>=a and
m+(k-1)d>=a componentwise. Decreasing coordinates bound k by
1+floor((m-a)/(-d)); increasing coordinates also impose the representation bound
floor((u64::MAX-m)/d). Zero-effect self-loops retain their input guards. The
resulting marking is m+k*d with checked arithmetic. The sparse helper requires
validated guards and unique, sorted effects, supplied by the existing graph.
Exhaustive small tests compare sparse bounds and dense repeated firing against
iterative firing, including disabling and overflow ordering.

The search retains single-step successors and adds the maximum permitted repeat
and each target-constraint crossing count. Crossing counts are heuristic hints,
including for mixed-sign and equality constraints; guards and final replay give
soundness. Additional repeated edges are limited to paths of one million firings
to bound trace expansion. This cap restricts added edges, not existing single
steps. More successors can consume the state budget sooner; no dominance claim
follows from retaining single steps.

Ancestry records (parent, transition, repeat count). The ordinary trace is expanded
and checked with the existing original-net witness replay before returning a
positive answer. Independent Python checking remains unchanged. Target relevance
projection and buffer lifting also retain their existing checks. Search
exhaustion, overflow or limits return Unknown, never a negative answer. Overall
process deadlines include witness construction and serialization; original-input
scheduling and the outer runner censor late results.

The motivating saved Circadian witness contains 100,000 consecutive firings.
That is an outcome-selected development case. A frozen same-binary factorial
comparison is needed before claiming even a local gain; broader regression and
Linux competitor comparisons remain separate requirements.
