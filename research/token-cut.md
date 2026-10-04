# Lazy token-flow cuts

The `token-cut` method solves the same fixed one-token-control token-moment relaxation as `token-moment`, using an explicit master over edge counts and final markings. It separates additional necessary constraints per original place. This implementation is under verification; no benchmark advantage or novelty is established.

## Master and proof boundary

Variables are nonnegative edge counts followed by nonnegative final markings. Rows encode the full original state equation, exact terminal controller marking, original target, and abstract control-flow balance. The count of an original transition is the sum of counts on all its abstract copies. Numerical LP optimization proposes rational candidate values; every row is then checked with arbitrary-precision rationals. Failed numerical optimization or reconstruction is unknown.

For edge e and original place p, source lower bound l is the original pre-arc weight. If p is a selected control place, both bounds instead equal its known source-mode marking (0 or1). Source enabling on selected places is already certified when rebuilding the control graph. Unselected places have no finite upper bound.

For fixed counts n and endpoint m, set residual flow f_e = y_e,p - l_e*n_e. Per-mode demand is

    b_q = [q=q0]*initial_p - [q=qf]*m_p
          - sum_out(q) l_e*n_e + sum_in(q) (l_e+delta_e,p)*n_e.

An exact common denominator converts candidate demands/capacities to integers. Their sum must be zero. Finite capacity is (u-l)*n; unbounded capacity remains infinite even when the candidate count is zero. The max-flow routine uses total positive demand+1 internally for infinity and rechecks any obstruction against the original infinite/finite capacities before returning it.

A violated subset S yields this universal master row:

    [qf in S]*m_p
    - sum_internal(S) delta_e,p*n_e
    - sum_entering(S) (l_e+delta_e,p)*n_e
    + sum_leaving(S) u_e*n_e
       >= [q0 in S]*initial_p.

A cut is invalid if any leaving edge has no finite upper bound. The candidate-dependent finite substitution never enters a universal row. Internal self-loops contribute their effects. These conditions follow by summing the residual flow balances over S. They apply to all concrete executions, independently of the candidate that exposed the cut.

## Search and certificates

The solver alternates exact-checked master refutations, exact-checked rational candidates, and per-place cut separation. It reuses cut descriptors across terminal modes, reconstructing the endpoint coefficient for each mode. Each original transition's summed integer count may guide concrete scheduling, but only original-net replay accepts a positive answer. Fractional candidates, failed scheduling, or a feasible relaxation alone cannot establish reachability.

`token-cut-v1` stores the certified control-place subset and one terminal proof per reachable abstract mode. Each terminal proof lists cut descriptors (place and sorted mode subset) and sparse Farkas multipliers over reconstructed master/cut rows. All terminal obligations must close for unreachability. The checker does not invoke a numerical solver or trust a max-flow result.

For a fixed abstraction there are finitely many subsets. With ideal exact LP feasibility and separation, new violated subset cuts suffice to decide this rational relaxation. The implementation's numerical candidate discovery, deadlines, dimension caps and128refinement limit can return unknown earlier. This is not a complete Petri-net reachability procedure. No integer branching, zero-count gating, bounded-cell refinement or general raw semilinear inclusion is present yet.

## Verification required before measurements

- Every generated concrete execution satisfies the master, per-place flow and each emitted cut for its terminal mode.
- Fixed-candidate full token-moment LP feasibility agrees with all-place flow feasibility, including zero-count infinite-capacity edges and initial=terminal cases.
- Independent Python reconstruction rejects malformed control sets, cut subsets, missing terminals, altered original arcs/targets and forged exact multipliers.
- The remaining g2 diagnostic must be rediscovered from the original net, and any measured speed or coverage comparison must use frozen binaries and equal budgets.

## Verified initial result

All152 Rust tests,37 independent Python certificate tests, and5 process-runner tests pass. g2 is automatically refuted with11flow cuts and2exact master models, covering all12terminal modes; its certificate passes independent Python reconstruction. Five alternating cold-process repetitions at5seconds solved it in both methods. Median observed wall time (including sampled-runner cleanup) was 0.1693s for full moments and 0.0408s for lazy cuts, a 4.15x ratio on this one known diagnostic. This is not broad benchmark evidence. Frozen binary/source: `results/solver-token-cut-v1`; run: `results/token-flow-g2-ablation`.

The independent audit established a limitation: without finite data bounds, admissible data cuts use successor-closed control subsets. A strongly connected control graph therefore gives no additional data strength beyond the state equation. Certified finite bounds and guarded partition refinement remain important future work.
