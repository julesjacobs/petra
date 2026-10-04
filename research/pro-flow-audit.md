# Independent audit of the proposed token-moment relaxation

Date: 2026-09-27. Source reviewed: `research/pro-publication-answer.md`, sections 3–5, 7 and 9–12. This audit derives the mathematics independently; it does not reproduce the consultation's reported probes, inspect their code, or establish a benchmark improvement or novelty priority.

## Finding

The execution-to-moment derivation and the per-place network-flow decomposition are sound under the stated abstraction obligations. Two implementation conditions deserve explicit checks: flow feasibility requires **zero total demand**, and **unbounded zero-count edges retain infinite capacity unless a justified branch also forces their moment to zero**. Cuts obtained under such a branch cannot be exported unconditionally.

The useful next gate is a checked fixed-abstraction reference implementation and differential tests against a flow separator. These findings do not justify replacing the existing solver or making a publication claim.

## 1. Semantic prerequisites

Let an original firing sequence induce a path through a finite partition `Q` of markings. For every original firing, there must be a corresponding abstract edge `e=(q,t,r)` with the original label `t`, original counter effect `delta_e`, and a domain `D_e` containing that firing's source marking. Restricting `D_e` to original enabling, source/destination cell conditions, or independently proved invariants is sound. An edge may be omitted only when its domain is proved impossible. A restricted enumeration of apparently reachable control states requires its own coverage/closure argument.

For box cells, valid coordinate bounds are obtained by intersecting source bounds, original enabling `x_p >= pre(t,p)`, and shifted destination bounds `L(r,p)-delta(t,p) <= x_p <= U(r,p)-delta(t,p)`. Bounds must include the domain of every concrete edge represented; tightening a bound from one observed execution is invalid.

The partition need only cover reachable markings if its coverage is certified by an invariant. Certified invariant bounds may eliminate otherwise possible cells. A merely guessed bounded controller does not satisfy this obligation.

## 2. Balances: independently derived

For a finite path with states `(q_k,x_k)`, let `n_e` count occurrences of `e`, and let `y_e` be the sum of `x_k` immediately before those occurrences. For each cell `q`:

```
sum_out(q) n_e - sum_in(q) n_e = [q=q0] - [q=qf]
sum_out(q) y_e - sum_in(q) (y_e + n_e delta_e)
    = [q=q0] x0 - [q=qf] xf.
```

Each interior visit contributes its marking once positively at departure and once negatively at arrival. Only the first and last states remain. This proves both equations even with repeated visits, self-loops, zero-length paths, and `q0=qf`. In the last case the right side of the moment equation at that cell is **`x0-xf`**, not zero.

Every source inequality `H_e x <= h_e` gives `H_e y_e <= h_e n_e` by summation. Thus every concrete path supplies an integer solution. Infeasibility of the rational relaxation proves absence of such a path; feasibility proves nothing about an executable ordering.

Summing the moment balances cancels every `y_e` and gives `xf=x0+sum_e n_e delta_e`. Keep the full original state equation, including coordinates not selected for moment reasoning. The abstract counts must obey `N_t=sum_{e:label(e)=t} n_e`. A particular original transition count is the **sum** of its edge-copy counts, not the value of each copy.

## 3. Per-place flow and an explicit cut formula

Fix counts and endpoint. For one coordinate `p`, write source bounds `l_e <= x_p <= u_e` and set `f_e=y_{e,p}-l_e n_e`. Then

```
0 <= f_e <= (u_e-l_e)n_e                   if u_e is finite
0 <= f_e                                 otherwise
outflow(q)-inflow(q) = b_q
b_q = [q=q0]x0_p - [q=qf]xf_p
      - sum_out(q) l_e n_e + sum_in(q)(l_e+delta_e,p)n_e.
```

All signs in the consultation match this derivation. The moments for different places are independent **conditional on the same counts and endpoint** when every domain is a box. Relational domain inequalities couple them and need a coupled LP or a sound weakening to boxes.

For `S subset Q`, summing the balance gives `b(S)=f(out(S))-f(in(S)) <= c(out(S))`. Here `out(S)` means edges crossing from `S` to its complement, not every edge whose source is in `S`. For finite outgoing bounds the symbolic cut is equivalently

```
[q0 in S] x0_p - [qf in S] xf_p
+ sum_{e internal to S} delta_e,p n_e
+ sum_{e entering S} (l_e+delta_e,p)n_e
- sum_{e leaving S} u_e n_e <= 0.
```

This form is useful for independently checking the matrix construction. Internal edges contribute their effects even though their residual flows cancel. Self-loops belong to the internal sum.

The subset cuts characterize capacitated-flow feasibility **together with `sum_q b_q=0`**. This follows from the usual supersource/supersink reduction: connect the supersource to positive-demand vertices and negative-demand vertices to the supersink, and check whether all positive demand can be routed. Original state-equation consistency supplies zero total demand here.

Counterexample to omitting that condition: one vertex, no edges, `b=-1`. Every subset upper cut holds, but its required balance `0=-1` is impossible. A checker/separator must either verify the original state equation at every proposed point or explicitly verify zero total demand before declaring a feasible flow.

With integral counts, endpoint, bounds and initial marking, all demands and finite capacities are integral, so an integral flow exists whenever a rational flow exists. This is integrality of the auxiliary moments, not an executable-order theorem and not integrality of the master relaxation.

An exact separation loop for a fixed graph, terminal cell and bounds has finitely many distinct subset cuts. If every iteration returns a genuinely violated new cut, it terminates for this fixed rational relaxation. This says nothing about termination under arbitrary partition refinement, integer branching, changing bounds, or approximate-master tolerances.

## 4. Infinite capacity at zero counts

An absent upper bound means that the homogenized constraints impose no upper bound on `y_e`. At `n_e=0`, the lower constraint only says `y_e>=0`. Therefore `f_e` retains infinite capacity. The expression `(infinity-l_e)*0` must **not** be evaluated as zero.

Minimal network counterexample: two vertices `A,B`, demands `b_A=1,b_B=-1`, and one unbounded residual edge `A->B` whose proposed count is zero. The homogenized subproblem is feasible with `f=1`. Setting that capacity to zero makes it infeasible. This is a local algebraic counterexample, not a claim that this particular master point comes from a Petri-net execution.

To exclude this recession flow while preserving all concrete integer paths, branch on

```
(n_e=0 and y_e=0) OR (n_e>=1).
```

The branch is exhaustive for concrete paths because edge occurrence counts are integers and the empty sum of source markings is zero. It is not exhaustive for the rational master relaxation, which allows `0<n_e<1`; negative reasoning must state that it covers integer executions rather than all rational points. Forcing `y_e=0` belongs only to the zero-count branch. A branch on `n_e=0` in the ungated LP alone does not logically imply it.

A cut obtained after removing such an edge depends on the branch premise. It must stay in that branch, or be stored as an implication/disjunction with the premise and checked accordingly. A globally reusable ungated cut cannot cross an outgoing edge with infinite capacity, even if that edge has zero count in the current candidate.

For one fixed feasibility call, replacing infinity by `B=sum_q max(b_q,0)` is sufficient to preserve feasibility (a feasible routing can discard cycles and route at most `B` along an edge); using a strictly larger value avoids ties involving replacement edges in minimum cuts. This value depends on the candidate. It is not a universal marking bound or a symbolic coefficient in a master cut. Before emitting a cut, explicitly reject any cut crossing an actually unbounded ungated edge. Numerical roundoff in `B` is another reason to reconstruct cuts exactly rather than trust the chosen finite capacity.

With `B=0` and zero total demand, zero flow already proves residual feasibility. A capacity substitution should not fabricate an obstruction in that case.

## 5. Terminal cells and projected control

The endpoint cell is fixed in each obligation. Proving one cell infeasible proves only that endpoint obligation. All target-compatible cells must be covered before a negative answer. The target and fixed control coordinates must be checked in the chosen cell. Reusing a cut across terminal cells requires reconstructing its terminal indicator term.

Simple counterexample to checking only the initial cell: an initial control token in `a`, transition `a -> b+g`, target `g>=1`. There is no target execution ending in control `a`, but the one-step execution ends in `b`. The certificate cannot infer whole-target unreachability from the `a` obligation.

Projected control stutters must be retained with original labels and data effects. For a single control cell and a transition producing one data token, deleting the projected self-loop falsely makes target `data>=1` unreachable. Even when its residual flow cancels, the transition contributes `n_e delta_e` to the moment balance. Original enabling must also remain: transitions with the same projected effect can have different original preconditions or data effects.

Copy-count error example: take two control cells, a switch from the first to the second, and an original transition `t` producing one data token without changing control. A concrete execution fires `t` once and switches, reaching data value one. If both copies of `t` are incorrectly constrained to equal the same integer `N_t`, the aggregate data effect becomes `2N_t`, and the reachable endpoint one may be rejected. Correctly, the two copy counts sum to `N_t`.

Conversely, allowing a different master count vector for every place only weakens the relaxation, potentially losing proofs. One cannot mix a cut computed at one per-place candidate with a different shared candidate and assume it is violated: the cut must be evaluated against the actual common master point. All cuts themselves remain universally valid if reconstructed correctly.

If a cell projection merges edges, the representation must retain enough original labels to reconstruct full effects and count sums. Deduplication by control endpoints or control effects alone is insufficient. Refinement changes edge identities: old cuts survive only through a checked aggregation map from refined copies to their original edge and a compatible cell/bound interpretation.

## 6. Dual claims and novelty limits

For fixed nonempty domains, a cell-affine potential `F_q(x)=a_q*x+b_q` satisfying `F_r(x+delta_e)<=F_q(x)` throughout every edge domain, initial value at most zero, and target value at least one is a valid negative proof by induction. Farkas certificates for fixed domains are linear in the potential coefficients and multipliers. Introducing the unknown invariant itself into the antecedent generally produces multiplier/coefficient products, so it is not the same LP formulation.

The consultation's lower-orthant limitation checks out. If `D_e={x>=pre_e}`, substitute `x=pre_e+z`, `z>=0`. Nonincrease for every `z` requires `a_r<=a_q` componentwise and `a_r*post_e+b_r<=a_q*pre_e+b_q`. Slopes must consequently coincide inside any strongly connected control component with those unrestricted domains. Splitting cells only to discover offsets can therefore reproduce an ordinary global linear potential when control is already a one-hot net component. Bounds, genuine phase changes, or richer joint control must supply additional power.

These arguments establish a sound class of separators, not arbitrary inductive polyhedra and not complete Petri-net reachability. A one-cell net with initial zero, transition `1 -> 2`, and target at least one remains a basic spurious-count example: count one, endpoint one, and any source moment at least one satisfy the moment constraints although no transition is initially enabled.

The audit establishes **no novelty priority**. State equations with CEGAR, Farkas-based affine/disjunctive synthesis, occupation-measure relaxations, network-flow duality and Benders decomposition are established mechanisms. The consultation's cited strengthened marking-equation, disjunctive-invariant and process-conformance papers require direct formulation-level reading before claiming that this particular combination is new. Describing a new implementation in Rust or an elementary consequence of max-flow duality as the core theoretical novelty would be insufficient.

## 7. Implementation gate

Before a performance experiment can support the proposed method:

1. Implement a fixed, certified control abstraction and full rational moment formulation as an oracle, retaining original transition labels, all stutters, count-sum constraints and the full state equation. Start with explicit terminal-cell obligations.
2. Check lifted summaries from bounded exhaustive/random concrete executions against **all** equations, including repeated controls, weighted read arcs, zero-length executions and `q0=qf`.
3. Differentially compare exact small flow feasibility against the full box-moment system; separately verify zero total demand. Exercise finite capacities, infinity, zero counts, self-loops and disconnected graphs.
4. Reconstruct every emitted subset cut independently from the original net, certified bounds and partition. Verify that it is violated by the exact candidate. Mutate edge omission, bound values, terminal cells, count-copy maps and infinite-edge treatment adversarially.
5. If zero-count gating is added, make its branching and branch-local cut premises explicit in the proof format. Never trust bounded-model failure, max-flow failure, timeout or floating infeasibility without an exact certificate covering the relevant obligation.
6. Establish whether this fixed relaxation adds proofs beyond existing methods on development data before investing in adaptive partition search. Compare eager moment LP with lazy cuts on the same abstraction and integrality treatment.

No builds or timings were run for this audit. The consultation's 400 subproblem comparisons, 285 cuts and 200 walks remain its reported probes, not independently reproduced results. This document supplies mathematical derivations and counterexamples, not measured solver performance.
