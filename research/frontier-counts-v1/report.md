# Native execution-frontier count refinement

Implemented optional `--method frontier-count-plan` in `src/frontier_counts.rs`.
The default and existing portfolio methods are unchanged. The solver proposes
integer firing counts, explores every execution permitted by those count bounds,
and either replays a target-reaching prefix or derives a necessary count constraint
from the complete exploration. Partial exploration yields unknown and no cut.

For candidate counts v, the execution frontier contains transitions enabled at an
explored state after all v[t] permitted occurrences have been used. If the graph
contains no target state, every witness must leave it; the first exit has total
count x[t] >= v[t]+1 for some frontier transition t. The solver retains the exact
disjunction. All-zero bounds use one sum >= 1 constraint, a singleton uses one
lower bound, and a general frontier uses nonnegative integer selectors bounded
above by one, with sum >= 1 and x[t] >= (v[t]+1)*selector[t]. Every witness extends
to a satisfying selector assignment. Every current candidate is excluded.

The state-equation count cap also counts selector variables; it is only a bounded
candidate-discovery policy. It has no negative authority. A missing integer model,
empty execution frontier, resource exhaustion, or arithmetic overflow returns
unknown. All positive answers replay on the original Problem. No new certificate
kind or checker trust is introduced.

Remaining active counts determine the marking through the state equation, so they
key the explored graph. Parent pointers reconstruct witnesses, including targets
reached before consuming all candidate counts. Total exploration respects the
requested state limit. Per-model storage is bounded by 16 million marking/count
cells; up to 128 models are attempted. These bounds do not establish completeness.

Six unit tests pass. They cover successful refinement of a read-arc obstruction,
positive-bound frontier constraints, interruption, arithmetic overflow, early
target prefixes, and the exact selector disjunction. A differential test covers
486 combinations of small weighted nets and count bounds; for each completed
target-free closure, every independently enumerated witness of length at most six
must cross the derived frontier. Clippy and the release CLI build pass. An initial
build failure from an ambiguous BigInt literal is preserved in the v1 unit log;
the corrected source passes in the v2 unit log.

The matched five-branch pilot has ten audited rows: both this solver and the frozen
state-budget count planner return unknown on every survivor branch at five seconds.
One candidate invocation expires externally; no sampled memory limit is exceeded.
RC02 branch 1 tries 51 models/cuts and 23,716 states; RC07 branch 0 tries 126
models/cuts and 76,070 states. TokenRing hits the 128-model limit with 476 states.
These observations demonstrate continued refinement, not improved coverage.

The separately registered complete 192-property development comparison is in
../frontier-counts-development-v1. It compares the standalone candidate, frozen
standalone count planner, frozen combined portfolio, and frozen existing solver
with shared one-second property budgets and independent answer checking.

This is an implementation experiment, not a novelty claim. Wimmel and Wolf,
Applying CEGAR to the Petri Net State Equation (LMCS 2012), already combine count
solutions, execution attempts and refinement. See ../related-work-audit.md. A
formula-level comparison with their jump/increment constraints remains required,
as do held-out/repeated comparisons and evidence of a substantial advantage.

Pilot plan SHA256: f63449655717c591ebc7aa0822cb1eb1b0d9051bb17f98fd835338838a906d28.
Pilot audit: audit.json; reproducible audit script: ../audit-frontier-counts-v1.py.
