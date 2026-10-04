# Independent review of grouped excess

Reviewed `src/grouped_excess.rs`, `tests/grouped_excess.rs`, and the separately
written `scripts/grouped_excess_checker.py` and its tests. No soundness blocker
was found. This review did not run solver benchmarks or predict checked coverage.

## Inductive invariant

Partition the places into nonempty groups. For group `g`, let `M_g` be its token
sum and choose a nonnegative integer threshold `h_g`. Define

    E(m) = sum_g max(M_g - h_g, 0),       B = E(m_initial).

For a transition, let `P_g` and `Q_g` be the sums of its original pre and post
weights in group `g`, and let `D_g = Q_g-P_g`. Enabling implies `M_g >= P_g`,
including read-arc contributions. The exact maximum group-excess change over
all scalar masses meeting that necessary enabling condition is

    U_g = D_g                                      if D_g >= 0;
          -min(-D_g, max(P_g-h_g,0))                if D_g < 0.

For nonnegative `D_g`, the change is at most `D_g` and attains it once both
arguments exceed the threshold. For negative `D_g`, the change decreases with
`M_g`, so its maximum occurs at `P_g`. Summing the separate maxima gives a valid
upper bound on the whole transition's change. If every transition satisfies
`sum_g U_g <= 0`, induction proves `E(m) <= B` at every reachable marking.
Group-wise enabling is weaker than original enabling; taking a maximum over
that larger set is conservative. No assumed place bound, net conservation,
reachability enumeration, or independence between actual group masses is needed.

Rust uses this closed formula. The Python checker instead evaluates the change
at the enabling boundary and both hinge breakpoints, clipped to the enabling
domain. These points include the constant tail, so its maximum is the same
exact scalar maximum. Both compute all sums and signed target arithmetic with
arbitrary-precision integers.

## Target exclusion

For one signed target row `a.m >= b`, put
`alpha_g = max(0, max_{p in g} a_p)`. Then

    a.m <= sum_g alpha_g*M_g
        <= sum_g alpha_g*h_g + B*max_g alpha_g.

A strict upper bound below `b` excludes that conjunct and therefore the whole
conjunctive target. Equality permits applying the same argument to either sign;
a greater-than-or-equal row permits only its original sign. Both implementations
enforce this restriction. Negative coefficients, zero thresholds, empty place
sets, large multiplicities, and read guards are compatible with the argument.
The discovery routine currently uses only threshold one and groups connected
by exact one-input/one-output unit transfers. This is a heuristic restriction;
the checker establishes induction for the supplied partition independently.

## Representation and research scope

The potential `E` is piecewise linear. Its sublevel set is a convex polyhedron:

    E(m) <= B
      iff for every subset S of groups,
          sum_{g in S} M_g <= B + sum_{g in S} h_g.

An equivalent compact extended formulation uses variables `e_g >= 0`,
`e_g >= M_g-h_g`, and `sum_g e_g <= B`. Thus this is a compactly represented
family of linear invariant inequalities, not a separation from general
polyhedral invariant analysis. The direct guard-aware induction test and sparse
group discovery may be useful operationally; novelty and performance need
separate evidence. Aggregate target bounds are conservative and can fail to
exclude a target even when the invariant excludes its conjunction.

The Rust and Python proof formats agree on their mathematical obligations.
Python additionally requires sorted place indices within each group; Rust's
discovery emits them sorted, so generated certificates meet that condition.
Rust accepts some harmless permutations that Python rejects. Resource exhaustion
returns failure or unknown and must never count as a checked negative result.
The existing original-input branch wrappers must check every required branch
before promoting a property-level negative answer.
