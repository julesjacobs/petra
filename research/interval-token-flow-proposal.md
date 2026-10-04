# Interval refinement of token flow: mathematical proposal

This is a design candidate, not an implemented or benchmarked solver. An agent derived the conditions without host computation during the timed runs; the coordinator independently checked the inclusion argument and parametric example. No novelty or completeness claim. Evaluate its relevance against the new192-property application suite before implementing it.

Partition selected counters into inclusive integer intervals [L,U], with adjacent intervals meeting at U+1 and a final unbounded interval if necessary. Combine their boxes with existing finite control. For an edge e=(q,t,q'), delta=post(t)-pre(t), use per-place pre-firing bounds:

    lower(p,e) = max(pre(p,t), L(p,q), L(p,q') - delta(p,t))
    upper(p,e) = min(U(p,q), U(p,q') - delta(p,t))

Include an edge only if lower<=upper for every selected place and existing control restrictions allow it. For a box alone this is exact one-step feasibility; additional correlated control restrictions may require separate checking or a sound overapproximation. An unselected counter has interval[0,infinity], tightened by certified bounds if available. Read arcs contribute their pre weight even when delta=0.

Use edge counts n_e and aggregate pre-firing token values y_(p,e):

    lower(p,e)*n_e <= y_(p,e) <= upper(p,e)*n_e

Omit an infinite upper bound. Choose an endpoint box qf and constrain the endpoint marking M by that box and the full conjunctive target. For each control state q:

    sum_out(n_e) - sum_in(n_e) = [q=q0] - [q=qf]
    sum_out(y_(p,e)) - sum_in(y_(p,e)+delta(p,t)*n_e)
        = [q=q0]*m0_p - [q=qf]*M_p

Every concrete run supplies a solution by summing its occurrences and pre-firing markings. Infeasibility therefore proves unreachability even if master counts are rational. Enumerate endpoint boxes, or enforce a correct endpoint disjunction; unbounded interval inequalities alone do not force endpoint variables to vanish at unselected boxes.

Refinement strengthens this relaxation. Map each refined box to its coarse parent and sum edge counts and token flows over edges with the same coarse image. Refined lower bounds are at least coarse lower bounds and refined upper bounds at most coarse upper bounds. Node balances project to the coarse balances. Preserve delta*n terms for edges that become coarse self-loops; their token effects do not disappear. The endpoint projects to its parent. Thus every refined solution gives a coarse solution.

## Parametric separation example

Places A,B,x,y start at(1,0,0,0), with k>=1:

    a: A -> B + k*x
    b: B + 2*k*x -> A + y
    target: (A,B,x,y) = (0,1,0,1)

The state equation admits counts n_a=2,n_b=1. The unsplit token-flow relaxation with exact A/B control is also feasible: aggregate x pre-values are y_xa=0,y_xb=2k, and aggregate y-counter pre-values are y_ya=1,y_yb=0. Exact A/B coordinate flows satisfy their fixed guards and balances.

Split x at2k into low=[0,2k-1] and high=[2k,infinity]. The target lies in B-low, which has no outgoing edge. Its only incoming edge is a:A-low->B-low. Count conservation forces that edge count to1. Token conservation gives M_x=y_xe+k>=k, contradicting M_x=0. Two intervals suffice independently of k, including with rational counts.

This example is also proved by the guard-aware linear inductive invariant x>=k*B: a establishes it, and b ends with B=0 and nonnegative x. The target satisfies the conservation equality x+k*y-k*B=0, so conservation equalities alone do not suffice. This is a strict separation from the state equation and unsplit aggregate flow, not a separation from linear-invariant analysis or standard abstract interpretation.

## Limits

An unbounded edge permits n_e=0,y_(p,e)>0. Leaving this possible is a sound but weak relaxation. Enforcing n_e=0 implies y=0 may be useful, but a min-cut obtained using that support restriction generally yields a conditional cut. It must not be added as an unconditional global linear cut without justification. A certified finite upper bound provides the globally valid upper*n coefficient.

Positive circulations can still invent token availability, and per-place flows do not synchronize cross-place ordering. Interval abstraction, flow separation, refinement and conditional affine invariants are established ingredients. Practical value, efficient refinement choices, independent proof checking, and differentiation from prior methods remain to be demonstrated.
