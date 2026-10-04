# Causal state-equation search

The `causal-state-equation` method combines the sparse state equation, bounded integer candidate discovery, forward support refinement, exact execution, and proof-producing refutation. It is an incomplete practical method, not a replacement for the separately implemented complete procedure. These ingredients overlap established state-equation CEGAR; no novelty claim is made.

For a place set S containing the initial support and a transition t with a preplace outside S, define F(S) to contain every original transition whose preplaces lie in S and which has a postplace outside S. Every concrete execution count vector satisfies

    x_t = 0  OR  sum_{u in F(S)} x_u >= 1.

If t fires, an outside place must first become marked. That first crossing transition lies in F(S). This argument retains full pre/post arcs, including weighted read arcs. F(S) is computed from all transitions, not just the candidate's support. Branches may overlap; they cover all concrete executions.

The solver asks sparse dual optimization for a refutation, then integer optimization for candidate counts. It closes the initial support under positive-count transitions and splits on a blocked candidate transition. It explores the enter branch first, then the omit branch. A complete proof tree requires an exact Farkas contradiction at every leaf. A candidate whose support is executable qualitatively still needs exact scheduling and original-net witness replay.

The 8192 total-count bound belongs only to candidate search. It never enters the proof system. Bounded infeasibility, failed realization, exhausted time, 128-node/48-depth limits and numerical reconstruction failures leave an obligation unknown. Reverse support from a candidate endpoint is not used as a universal cut: other candidate endpoints can have different support.

`causal-state-equation-v1` records a tree of support splits and sparse Farkas leaves. Both the Rust checker and the independent Python checker reconstruct the state equation and each ancestor row. Neither trusts a supplied frontier, numerical status, or search bound. The Python checker independently combines place weights and checks original transition arcs, rather than calling the Rust matrix builder.

`portfolio-causal` is an explicitly experimental scheduling ablation: give causal search 20% of the budget, capped at 500ms, then give the remaining time to v2. Default remains v2. Full coverage and costs must be measured; a union of separate method results is not a portfolio measurement.
