# Exact SAT encoding for acyclic control

`dag-sat` is a native Rust portfolio component for ordinary weighted Petri nets
with a certified acyclic one-token control projection. `portfolio-symbolic`
tries this component before the existing focused portfolio. This is not a
complete procedure for arbitrary Petri nets; a missing certificate, reachable
control cycle, or resource limit returns unknown. No place or transition names
are recognized, and the source Boolean formula is not used.

## Exactness argument

The control certificate is a set of original places whose initial token sum is
one and whose consumed and produced token sums agree on every original
transition. The existing exact control checker proves these equalities.
A transition consuming two or more control tokens is therefore disabled.
A transition consuming one control token has a unique control source and
target. A transition consuming none would permit control stuttering; this
component rejects such projections. The reachable control graph must be a DAG.

Every execution consequently visits control vertices at most once. Allocate
one Boolean selection variable per reachable control edge. At each vertex,
at most one incoming edge and at most one outgoing edge may be selected.
Every selected outgoing edge requires a selected incoming edge, except at
the initial vertex. Following predecessors in the DAG shows that every
selected edge belongs to a single path from the initial vertex. Paths may
stop anywhere, including before firing any transition. Conversely, every
such path satisfies these clauses.

Order edges topologically by their control source. Maintain a bit-vector
marking while scanning edges in that order. A selected edge must satisfy
every original weighted preset and updates each changed place by its exact
post-minus-pre effect; an unselected edge leaves the marking unchanged.
This scan follows the selected path in execution order. Read arcs remain
guards even when their net effect is zero.

The second encoding derives control markings directly from the selected
path: a control place is marked at termination exactly when it was entered
(or was initially marked) and no outgoing edge was selected. The certified
path already guarantees the control preset for each selected transition,
so no control-counter adder or repeated control guard is needed. Data-place
guards and arithmetic are unchanged. The current proof kind is
`dag-cnf-rup-v2`; `dag-cnf-rup-v1` still regenerates the first encoding to
preserve verification of frozen certificates.

For each data place, the initial marking plus the sum of all positive edge
effects is a finite upper bound. For control places, the certified one-token
sum gives bound one. Arbitrary-precision bound calculation supplies enough
bits for exact values, including values exceeding u64. Guarded subtraction
cannot underflow on a selected edge. Thus truncation in the bit-vector
adder cannot change a represented execution. Conditional updates for
unselected edges have no semantic effect.

Signed linear target constraints are moved to two unsigned sums. For
`a*m >= b`, compare `sum(a_positive*m)+max(-b,0)` against
`sum((-a_negative)*m)+max(b,0)`. Equality compares all bits. Bounds include
every coefficient and constant, including i64::MIN. AND/XOR gate clauses
are equivalences; arithmetic is exact rather than a relaxation.

It follows that the resulting CNF is satisfiable exactly when the original
target is reachable for this certified class. A positive assignment is
additionally decoded and replayed on the original net. The current witness
format uses u64 markings, so a mathematically valid witness requiring a
larger intermediate value returns unknown instead of a false answer.

## Negative proof boundary

Varisat proposes a model or refutation. SAT assignments are checked against
every generated clause before original-net replay. Negative certificates
contain only the control places and RUP clause additions. Both the Rust
checker and a separate Python implementation regenerate the CNF from the
original weighted net and target, check control conservation and acyclicity,
and check each learned clause by unit propagation under its negation. The
last addition must be the empty clause. Proof deletions are discarded;
retaining earlier clauses preserves RUP validity. Non-RUP steps or incomplete
proofs yield unknown. An implicit contradiction during input loading is
made explicit by appending an empty clause, which must pass the same checker.

The SAT engine is pinned Varisat 0.2.2, with the small documented interruption
patch in `vendor/varisat/PATCH.md`. It does not change SAT heuristics or
learning rules. Input, proof, encoding, and checker work are bounded, and
late results are rejected. Cooperative deadlines supplement the benchmark's
outer process and memory limits. The vendored dependency belongs in every
source freeze. Existing upstream warnings remain visible in build logs.

## Validation and research status

Tests compare CNF satisfiability with independent arbitrary-precision firing
and exhaustive BFS on small weighted DAG nets; cover merges, shuffled place
and transition order, read arcs, arbitrary stopping, signed/equality goals,
disabled multi-control transitions, oversized guards and values beyond u64;
and compare every CNF variable, clause and choice between Rust and Python.
SAT wrapper tests compare 160 small formulas with truth tables, reject
forged RUP steps and check interruption without waiting for a proof write.
Integration tests replay positives and reject a negative proof after the
original target changes. The Python checker also runs under `-O`.

This is an application of SAT encoding and certified structural bounds, not
a demonstrated new reachability theorem or publication novelty claim.
Measurements must establish its usefulness on the full generated development
suite and its cost on the application corpus. The reserved evaluation
families remain outside tuning.
