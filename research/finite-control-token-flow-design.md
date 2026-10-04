# Finite control projections for token-flow separation

The existing token-flow engine requires a conserved set of places containing
exactly one token. In the full classical SMPT comparison, 23 of 37 queries have
24 branch outcomes reporting that no such control abstraction was found. The
sparse implementation preserves coverage but does not remove this restriction.

The extension uses the same master inequalities, exact flow separator and
Farkas proof arithmetic with a finite projection of certified bounded counters.
It is an incomplete reachability engine. Finite projection and place invariants
are established techniques; this implementation does not establish novelty.

## Projection invariant

Choose original places S. For each selected place p, independently check a
nonnegative potential w with w·post(t) <= w·pre(t) for every original transition.
Then m[p] <= floor((w·m0)/w[p]) whenever w[p] > 0. The smallest certified bound
for each selected place defines its finite range.

Build the reachable projected graph by deterministic breadth-first traversal,
starting from m0 restricted to S. At each mode, visit every original transition
in input order. Check every selected input weight, subtract inputs, add outputs,
and retain the successor when it remains within the certified ranges. Preserve
reads, stutters, parallel transitions and original transition identities. Ignore
unselected guards only in this graph construction. Reject incomplete graphs
when resource limits are reached. An empty selected set has one mode and a
stuttering edge for every original transition.

Every concrete execution projects to a graph path. The induction step uses
original enabling to discharge selected guards and the independently checked
invariants to discharge range checks. Thus dropping out-of-range successors is
sound even when the projected graph includes spurious states caused by ignored
guards or correlations between counters.

## Shared token-flow constraints

Keep edge-count variables and final variables for all original places. The
master retains original incidence equations, target inequalities, and graph
flow conservation. For terminal q, fix each selected final coordinate p to
q[p]. For an edge starting at q, its selected-place source moment is exactly
q[p] times its count. For an unselected place, retain the original enabling
lower bound and any certified finite upper bound.

The existing per-place capacitated-flow separator applies unchanged to these
source bounds. A cut names an original place and a subset of graph modes.
Finite upper bounds still require original-net potential certificates; an
algorithmic replacement for infinity is never exported as an invariant.

A negative certificate checks a Farkas contradiction for every reconstructed
terminal mode. Every concrete target-reaching run has some terminal mode and
would satisfy all its reconstructed inequalities, contradicting that leaf.
A positive answer still requires replaying an original transition sequence.

## Certificate boundary

`finite-token-cut-v1` contains only `kind`, sorted `controls`, `bounds`, and
`terminals`. Its bound certificate uses `place-bounds-v1`; each terminal uses
the existing `cuts` and `multipliers` representation. No supplied graph or
claimed mode values are trusted. Rust and the independent Python checker
reconstruct the graph, master and cut rows from original weighted arcs.

The new proof kind leaves legacy one-token certificates unchanged. Shared
graph access abstracts only topology and exact selected coordinate values;
shape validation alone is not the certificate's semantic validation.

The independent Python checker uses explicit validation, including under
`python -O`. Its tests check every generated master and cut inequality against
concrete prefixes of a small weighted net, reject malformed potentials and
Farkas proofs, and exercise graph limits. A Rust-generated negative certificate
for the two-token cyclic fixture passes that independent checker.

## Evidence still required

The cyclic fixture shows that the engine can handle a control representation
outside the previous one-token restriction. It does not establish superiority
over other reachability methods. Full Rust regressions, saved-proof
compatibility, paired application benchmarks and longer-budget evaluation
remain required before a performance claim. The current discovery policy
selects target-related bounded coordinates under graph limits; it is not yet
counterexample-driven refinement with retained cuts between projections.
