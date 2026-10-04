# Same-marking count dominance

Status: mathematical proposal and implementation contract. The separation below
is exact; it is not a performance result or a novelty claim. It concerns count
frontier refinement, including Boolean support refinements, rather than the
whole solver portfolio.

## Checked closure and the frontier theorem

Let a Petri net have initial marking `m0`, transitions `T`, incidence matrix `C`,
and any target predicate `P` on exact markings. Weighted arcs and read arcs use
their original enabling conditions. Fix finite bounds `v in N^T`. A retained
prefix is `(m,u)`, where `u <= v` is its used-count vector and
`m = m0 + C*u`. At the same marking, `(m,u)` dominates `(m,w)` when `u <= w`
componentwise: it leaves at least as much of every transition's budget.

A finite retained set `Q` and frontier `F subseteq T` justify a cut if an
independent checker establishes all these conditions:

1. Every stored marking and count is a nonnegative integer, `u <= v`, and
   `m = m0 + C*u`. The initial pair `(m0,0)` belongs to `Q`.
2. Every marking represented in `Q` fails `P`.
3. For every `(m,u)` in `Q` and every original transition `t` enabled at `m`:
   - If `u[t] < v[t]`, some `(m',u')` in `Q` satisfies
     `m' = fire(m,t)` and `u' <= u + e_t` componentwise.
   - If `u[t] = v[t]`, then `t` belongs to `F`.

All original transitions must be considered, including transitions with bound
zero. Exact marking equality in the successor condition is essential. Individual
representatives need not carry replay traces for the negative theorem: the
checked initialization and closure conditions suffice. A witness still needs
its actual original-transition trace and replay.

**Theorem.** Every target-reaching execution has total count vector `x` satisfying

    OR over t in F: x[t] >= v[t] + 1.

**Proof.** Suppose a target-reaching execution violates this disjunction, so
`x[t] <= v[t]` for every `t in F`. Induct along its prefixes. For each actual
prefix with marking `m` and counts `h`, maintain a retained representative
`(m,u)` with `u <= h`. Initialization uses `(m0,0)`. If the next transition is
`t`, exact marking equality means it is enabled at the representative. If its
budget there is exhausted, then `t in F` and the execution's next prefix has
`h[t]+1 >= u[t]+1 = v[t]+1`, contradicting the bound on its total count.
Otherwise closure supplies a representative of the exact successor with
`u' <= u+e_t <= h+e_t`. At the final prefix a retained marking satisfies `P`,
contradicting target exclusion. This proves the disjunction.

The proof does not assume that `v` satisfies the state equation or target. It
also does not require target monotonicity or componentwise marking dominance.

**Empty frontier.** If `F` is empty, the theorem proves global unreachability.
Equivalently, the markings represented in `Q` form a finite inductive set:
initial inclusion, original-transition closure, and target exclusion are all
checked. An implementation that lacks a certificate for this result must keep
returning `unknown`; a mathematically valid internal closure is not an exported
checked negative answer by itself.

## Worklist implementation obligations

For each exact marking, retain an antichain of componentwise-minimal used-count
vectors, equivalently componentwise-maximal remaining-count vectors. A generated
prefix can be omitted only when such a representative dominates it. Incomparable
vectors must both remain. One arbitrary vector per marking is insufficient.

When a new vector dominates old vectors, remove the old vectors from the active
antichain and eventually expand the new vector. Stored parent records may remain
for witness reconstruction. A removed vector needs no expansion: the replacement
has the same marking and at least its remaining budget. Further replacements
preserve this coverage by transitivity. Queue exhaustion establishes a cut only
after all still-active representatives have had all enabled transitions checked.

Previously collected frontier entries from later-removed representatives may be
retained: they enlarge `F` and therefore weaken the valid disjunction. To obtain
the smallest frontier, reconstruct it from the final active representatives.
In particular, stale entries can prevent recognition of an empty frontier.

For fixed finite `v`, at most `product_t (v[t]+1)` distinct used-count vectors
exist, and each fixes its marking. A correctly maintained antichain worklist
therefore terminates without resource limits. A removed or rejected vector can
never need reinsertion: the current representative dominating it may itself be
replaced only by a componentwise-smaller vector at the same marking. This does
not give a useful polynomial bound. Incomparable vectors, different markings,
and antichain comparison cost can still be large.

Deadline, arithmetic, storage, or state-budget exhaustion before these closure
conditions hold permits a replayed positive witness or `unknown`, never a cut.
The theorem gives no termination guarantee for the outer unbounded sequence of
integer-model queries and refinements.

There is a conditional completeness fact for bounded nets. For each reachable
marking, take the componentwise-minimal counts among all prefixes reaching it.
Dickson's lemma makes this basis finite. If the reachable marking set is finite,
the union of these bases is finite. Choose `v` strictly above every coordinate
of every vector in the union. Exhaustive dominance exploration then retains
exactly these minimal vectors: each has a bounded executable prefix, and every
other vector is dominated by one of them. No retained vector exhausts any
transition budget, so target-free closure has an empty frontier. Thus an
externally chosen sequence of bounds eventually exceeding every fixed vector
decides reachability on bounded nets, assuming exhaustive work at each bound.
The present integer-model selection policy need not generate such a sequence;
this is not its termination theorem. Ordinary marking exploration already has
bounded-net completeness and may avoid the count-vector overhead entirely.

## A 1-safe family on which original refinement continues forever

For any `r >= 2`, use control places `p_0,...,p_(r-1)` and place `z`. Initially
only `p_0` contains a token. Indices below are modulo `r`:

    t_i: p_i -> p_(i+1)                 for 0 <= i < r
    c:   p_0 + p_1 -> p_0 + p_1 + z
    target: p_0=1, every other p_i=0, z=1

All arc weights are one. The invariant `sum_i p_i = 1` prevents `c` from ever
firing. The exact reachable markings are the `r` single-control-token markings
with `z=0`; the net is globally 1-safe, and the target is unreachable.

Nevertheless, the state equation for the target admits exactly the count family

    v[t_i] = k for every i,    v[c] = 1,    k in N.

For every `k >= 1` these candidates pass both forward and reverse Boolean
support checks. Forward support traverses the cycle without deleting marked
places, obtaining all `p_i`, then supports `c`. Reverse support starts at the
target and traverses the reversed cycle, again obtaining all `p_i`; its initial
`z` token also supports the reverse of `c`. These are the support semantics in
`src/count_plan.rs::support_failure` and the forward support semantics in
`src/causal.rs::blocked_support`. They ignore multiplicity and simultaneous token
availability, as required for their necessary support condition. The `k=0`
candidate may be excluded by support refinement; every `k >= 1` survives.

The candidates also satisfy ordinary marked-trap and initially-empty-siphon
constraints. An initially marked trap contains `p_0`; closure under each `t_i`
forces it to contain every control place, so the target intersects it. A siphon
containing any control place contains every control place by following incoming
cycle edges, so it is initially marked. The only possible nonempty initially
empty set left is `{z}`, which is not a siphon because `c` produces `z` while
consuming no `z`. Thus no nonempty initially empty siphon excludes the target.

Fix `k >= 1`. Exact count-bounded exploration visits the unique cycle prefix of
each length `0,...,r*k`. These are `r*k+1` distinct used-count vectors but only
`r` different markings. Before the last prefix, the sole enabled cycle
transition has remaining budget. At the last prefix the marking is initial and
`t_0` is exhausted. Transition `c` is never enabled. Consequently the original
frontier is exactly `{t_0}` and its cut is

    x[t_0] >= k+1.

Together with the state equation this merely requires a larger common cycle
count. Every finite collection of these cuts admits another integer candidate
`k` above all previous bounds, and all such candidates still pass the support
and structural conditions above. An ideal unlimited implementation that refines
only by these frontiers can therefore continue forever on this finite-state
unreachable instance. With the current caps it returns `unknown`; the theorem
does not predict a particular numerical solver's candidate order.

In contrast, same-marking count dominance retains exactly the first `r` cycle
prefixes. At the final cycle step the initial pair dominates the generated pair.
For every retained pair, its unique enabled cycle transition still has budget
because `k >= 1`. The final frontier is empty. This closes the net after `r`
retained representatives, independently of `k`.

For the smallest member (`r=2`), original enumeration requires `2*k+1` vectors
against two retained dominance representatives. If successive candidates use
the smallest surviving values `k=1,...,n`, original refinement visits
`r*n*(n+1)/2+n` vectors over `n` unsuccessful closures; dominance closes its
first support-feasible candidate. These are exact state counts, not timings.

This separates the two count-frontier algorithms even after Boolean support,
marked-trap and initially-empty-siphon refinement. It does not separate dominance
from exact marking exploration, which also closes the `r`-state graph, or from
guard-aware invariant analysis: the invariant `sum_i p_i=1` immediately proves
`c` disabled. Preprocessing can remove this example before either search runs.

## Research boundary

Dominance on remaining resources is a familiar simulation principle; count
realization and state-equation refinement already have close prior art. The
specific first-exit theorem and example establish soundness and a limitation of
the present enumeration, not novelty or improvement on development survivors.
Before promoting the mechanism, measure how many survivor prefixes share an
exact marking and how many of their count vectors are comparable. Large
same-marking multiplicity alone does not establish useful dominance. Compare
against the existing frontier planner and ordinary reduced marking search at
matched budgets, preserving checking and failure outcomes.
