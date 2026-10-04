# Complete generalized-VASS decomposition: implementation contract

The implementation follows Kosaraju's generalized-VASS decomposition, as presented in S. Lasota, *VASS reachability in three steps*, arXiv:1812.11966v3, §§2–3, available locally as `research/lasota.txt`. That note explicitly describes itself as intuitive and incomplete. The points below supply implementation obligations and corrections; they are derived checks, not claims of a mechanically verified implementation.

## Representation and exact input reduction

A component has a finite directed multigraph of pure-effect VASS edges, entry/exit states, and natural-valued endpoint coordinates, each fixed or free. A rigid coordinate has zero effect on every internal edge and the same **known** fixed value at both endpoints. Components are linked in a sequence by one mandatory pure-effect edge apiece. All intermediate markings must be nonnegative. Parallel edges remain distinct.

A Petri-net transition with both input and output arcs requires an atomic consume/produce pair through a private control state. Collapsing it to its net effect loses read-arc enabling conditions. Each transition's intermediate state permits only its production edge.

Linear targets require an exact reduction or exact endpoint arithmetic. Merely choosing one satisfying target point destroys completeness. A useful reduction drains the original marking into positive and negative accumulators for each constraint, then cancels paired accumulator tokens; equality requires both residuals zero, inequality permits draining positive surplus. Constants are inserted on the target-phase entry edge. The final zero marking must be reached in a distinct accepting control state, with no return to original transitions after entering the target phase.

## Characteristic integer system

Use integer nonnegative entry vectors x_i, exit vectors y_i and transition-count vectors f_i. Add fixed endpoint equalities, conservation y_i=x_i+C_i f_i, control-state Kirchhoff equalities, and link equalities x_(i+1)=y_i+z_i. Rigid values are ordinary endpoint equalities. Link nonnegativity follows because both endpoint vectors are nonnegative.

The base system uses **f_i≥0**, not f_i≥1. Every real run satisfies it, so integer infeasibility safely rejects. It can contain disconnected circulations; a feasible model alone never proves reachability.

After normalizing components to SCCs, mark every internal transition count and every free endpoint coordinate. Theta1 requires simultaneous unboundedness of all marked variables. For this rational polyhedron with integer coefficients and nonnegative variables, if there is an integer base solution and each marked variable has a nonnegative homogeneous rational recession ray positive in that variable, scaling rays to integers and summing them gives simultaneous integer unboundedness. With all internal counts positive, Kirchhoff plus connected support gives an Euler trail, which recovers the pseudo-runs used in Theta1.

If some marked variable has no such recession ray, it has a finite rational upper bound over the feasible polyhedron. An exact ceiling of that bound is a safe integer enumeration limit. Optimizing over the rational relaxation may be used to derive a conservative bound; floating-point values are insufficient without checked rounding. Integer feasibility still requires a complete exact integer decision procedure.

**Missing-support pitfall in the exposition:** Lasota's set L imposes f≥1. Its emptiness does not imply the absence of a real run: a run can omit an arc. Working with f≥0 throughout avoids this issue. Alternatively one must explicitly branch on omitted arcs before reasoning from the f≥1 system.

## Theta1 refinements

For an internal edge whose count is at most c, enumerate k=0,…,c. Replace its component by k+1 copies with that edge removed, joined by k mandatory copies of that edge. The first copy inherits original initial constraints; the last inherits original final constraints. All newly internal endpoints are free except rigid coordinates, which retain their fixed value. Correct entry/exit states of each copy must match the split edge's source/target. Repeated edge copies are distinguished occurrence positions.

For a free endpoint coordinate bounded by c, enumerate its fixed value 0,…,c. Do not constrain both endpoints simultaneously unless the characteristic equations imply that relation.

## Theta2 and pathwise bounds

For each component, project onto its initially fixed nonrigid coordinates and run Karp–Miller from its initial values. Theta2 requires a self-covering cycle at the entry state strictly increasing **all** these projected coordinates. Equivalently the projected coverability tree reaches an all-omega label: strong graph connectivity allows returning to the entry state once all projected counters are arbitrarily large. Repeat symmetrically on reversed edges from the exit state and its fixed coordinates. An empty projected coordinate set makes this condition vacuous.

When the condition fails, extract a finite c such that **each entire concrete run has at least one initially fixed coordinate that remains ≤c throughout that run**. This is stronger than saying each reached marking has some coordinate ≤c, since the identity of the coordinate must remain fixed along the run.

A genuine ancestor-based Karp–Miller tree supports this bound: take the maximum finite label across the tree. Along a branch, omega coordinates never become finite; a terminal label with a finite coordinate witnesses the fixed bounded coordinate. Concrete continuations covered by an ancestor repeat are accounted for by the ancestor relation and acceleration. Arbitrary global cross-branch subsumption needs its own proof before it can supply this pathwise bound. A plain finite coverability basis by itself is insufficient evidence for the stronger property.

For each candidate bounded coordinate j, if the opposite endpoint is free, first enumerate its value 0,…,c. If both endpoints are fixed a,a', keep coordinate j in [0,c] by a control-state product. Store its actual value in the control state; set its internal effect to zero and rigid endpoint value to a. Append a mandatory adjustment edge with effect a'−a and an edge-free component preserving the original final endpoint constraints. This reconnects to following links using the original final coordinate a'. Reject the branch if either fixed endpoint exceeds c. The reverse-direction refinement is symmetric; prefix adjustment is also possible if endpoint/link constraints are transformed consistently.

## Termination rank and corner cases

For each component use lexicographic rank (number of nonrigid coordinates, number of internal edges, number of free endpoint coordinates), and order finite multisets of these ranks by the well-founded multiset extension.

* Bounded-edge splitting replaces one component by finitely many components with fewer internal edges.
* Endpoint fixing decreases the last rank coordinate.
* Bounded-coordinate unfolding decreases the first coordinate regardless of graph expansion. Its adjustment component must also have lower rank; make all originally rigid coordinates and j rigid there, with their post-adjustment values.
* SCC decomposition removes connectors from internal edge sets. First remove states/edges not on an entry-to-exit path without recursive rank claims. Otherwise a discarded isolated state could leave an identical rank. Every genuine multi-SCC path uses an inter-SCC edge, so its retained components have fewer internal edges.

An edge-free singleton is strongly connected under the length-zero convention. Its entry/exit states must coincide and its marking cannot change. Characteristic equalities decide inconsistent fixed values. Coordinates fixed at one endpoint bound free coordinates at the other, so Theta1 refinement can fix them. Coordinates fixed at both endpoints and unchanged may be made rigid. Coordinates free at both endpoints must remain free unless global linkage proves their fixed value: replacing an unknown rigid-looking value by zero is unsound. Theta2 on no fixed nonrigid coordinates succeeds vacuously; Theta1 can succeed through free endpoints alone.

Finite timeout, integer/coordinate overflow, expansion limits, or an incomplete ILP backend yield unknown. They cannot reject a branch. Resource-bounded implementations are a complete mathematical procedure only if every artificial bound is removable and all unbounded constituent procedures terminate on finite inputs.

## Independent adversarial checks to require

1. A direct witness omits an internal SCC edge; the full-support characteristic system is infeasible.
2. Read/self-loop arc with insufficient initial tokens despite zero net effect.
3. Zero-edge singleton and zero-dimensional projection.
4. Globally linked free coordinates whose required fixed value is positive, with zero internal effect.
5. Bounded edge occurring zero, one, and multiple times; endpoint constraints apply only to outermost copies.
6. Failed forward pumping with one of several coordinates bounded along different runs.
7. Bounded-coordinate unfold where a≠a' and the component has a following link.
8. Reverse pumping failure and final-to-initial constraint mapping.
9. Integer-infeasible but rational-feasible characteristic equations.
10. All results cross-checked on finite bounded nets against exhaustive reachability, including impossible non-point linear targets.
