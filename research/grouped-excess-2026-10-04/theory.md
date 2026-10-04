# Grouped excess bounds

The `grouped-excess` engine proves a target unreachable using an inductive bound
on the total excess above group thresholds. `portfolio-excess` tries this engine
before the reductions and search used by `portfolio-reduced`. Discovery is
incomplete; an unsuccessful attempt returns `unknown` and the portfolio continues.

## Invariant

Partition the places into nonempty groups G and choose nonnegative integer
thresholds h_G. Write x_G(m) for the sum of tokens in group G and define

    E(m) = Σ_G max(x_G(m) − h_G, 0).

For each transition, let P_G and Q_G be its total input and output multiplicities
in G, including both sides of read arcs, and let D_G = Q_G − P_G. An enabled
marking satisfies x_G ≥ P_G. Over every such group mass, the maximum change in
the group's excess is

    D_G                                  if D_G ≥ 0,
    −min(−D_G, max(P_G − h_G, 0))         if D_G < 0.

For a nonnegative delta the difference never exceeds the delta, and reaches it
above the threshold. For a negative delta the difference is nonincreasing in the
starting mass; its maximum is attained at P_G. Thus, if the sum of these maxima
is nonpositive for every transition, E cannot increase on a firing. This checks
all original transitions and all enabled markings, without enumerating markings.
Consequently every reachable marking satisfies E(m) ≤ B = E(initial).

## Target exclusion

For a target row a·m ≥ b, define α_G = max(0, max_{p∈G} a_p). Nonnegative
markings satisfying E(m) ≤ B obey

    a·m ≤ Σ_G α_G h_G + B max_G α_G.

Each group can contribute at most its threshold mass without spending excess;
all remaining mass spends the common budget B. Assigning that budget the largest
coefficient gives a sound upper bound. An upper bound strictly below b excludes
the target. An equality can also be tested after negating its coefficients and
bound. A negative sign is rejected for an inequality.

The bound uses arbitrary-precision integers. It remains sound with weighted
arcs, large markings, mixed-sign target coefficients and read arcs. A conjunction
is refuted when one row is excluded; disjunctive properties retain the original
whole-property scheduler and require every branch to be refuted.

## Discovery and certificates

Discovery unions places connected by transitions whose complete input and output
each consist of one unit arc. Every other place starts as a singleton. The current
discovery algorithm uses threshold one for every group. These choices only propose
a candidate; the invariant check decides whether it is valid.

The `grouped-excess-v1` certificate contains the partition, thresholds, target-row
index and sign. Checkers recompute B, transition bounds and target exclusion from
the supplied problem. The independent Python checker computes each transition
bound by evaluating piecewise-linear breakpoints, separately from the Rust closed
formula. It validates the certificate even under `python -O`.

Tests compare discovery with exhaustive exploration of bounded weighted nets and
reject malformed certificates. The independent review is in [review.md](review.md).
Campaign evidence is separate in [the comparison directory](../grouped-excess-20261004/).

## Expressiveness

E is piecewise linear, and E(m) ≤ B is a convex polyhedron: it is equivalent to
the inequalities Σ_{G∈S}(x_G − h_G) ≤ B for every subset S of groups. The compact
form can encode exponentially many inequalities, but is not more expressive than
general polyhedral invariants. No novelty or general solver superiority is claimed.
