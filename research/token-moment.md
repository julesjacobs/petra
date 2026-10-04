# Fixed-control token-moment reference

Work in progress, following the completed Pro proposal and independent derivation in `pro-flow-audit.md`. This is an implementation of a sound relaxation, not a novelty or performance claim. The current version constructs the full sparse LP; no min-cut separation, adaptive interval partitioning, zero-count gating, integer proof branching or direct semilinear inclusion is implemented yet.

`control.rs` proposes a subset of places whose total initial marking is one and whose total is conserved by every original transition. Binary optimization searches without consulting names or manually supplied phases. Exact integer checking validates conservation. The graph enumerates every reachable one-token control mode while forgetting data enabling; control-stuttering transitions are retained, and weighted control reads requiring two tokens are correctly disabled. The graph is rebuilt by the proof checker. This overapproximates every concrete execution by induction on the original transition sequence.

For each graph edge e introduce a nonnegative firing count n_e, and for each original place p a nonnegative source moment y_e,p. A concrete run maps y_e,p to the sum of that place's marking immediately before all occurrences of e. Final marking variables m_p are shared across the constraints.

The reference LP has these rows, in certificate order:

1. Full original state equation m_p - sum_e delta_e,p*n_e = initial_p.
2. Fixed terminal control marking, for every selected control place.
3. Original target, in its original order.
4. For each control mode q: flow balance, then token-moment balance for every original place.
5. For each edge: original pre-arc moment lower bounds y_e,p >= pre_e,p*n_e, then exact selected-control source moments.

Each equality appends its negative >= row before its positive >= row. Terms are combined by variable index and zero terms removed. Variable order is edge counts, final marking, then edge-major source moments. This deliberate full reference retains redundant rows and moments on control places for transparent testing. Later sparse separation must preserve its proof power on the same abstraction.

Token-moment balance is

    sum_out(q) y_e,p - sum_in(q) (y_e,p + delta_e,p*n_e)
        + [q=qf]*m_p = [q=q0]*initial_p.

All actual executions satisfy it by cancellation of intermediate markings. A terminal obligation is refuted only with an exact sparse Farkas certificate. `token-moment-v1` contains a checked control subset and one proof for every reachable abstract terminal mode, in graph traversal order. Original enabling and target are reconstructed from the net; missing terminal proofs are rejected. Feasible arithmetic alone never supplies a positive answer.

The full reference LP uses up to 100,000 variables and the controller has at most 8,192 edges. Limit failures yield unknown. Discovery is incomplete, and one-token controllers alone cannot model arbitrary bounded concurrency. The natural next step is an exact per-place flow separator, validated against these constraints before using its cuts in a master search.
