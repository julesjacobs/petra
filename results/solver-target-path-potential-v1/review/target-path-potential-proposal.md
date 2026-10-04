# Checked target-path potentials as ordinary slack-place guards

**Minimal proposal:** after target-zero trap reduction, try one incidence-derived
candidate: the all-ones place vector. If its value never decreases and the target
provides finite coordinate upper bounds, add one slack place enforcing the derived
sum bound. Keep the existing engines and their schedules. This is a proposal;
no solver run, implementation, speed claim or novelty claim accompanies it.

## Exact distinction and reduction

Let C_t = post_t - pre_t. A **target-path potential** consists of nonnegative
integer weights w and an integer bound B, checked to satisfy:

1. w·C_t >= 0 for every original transition t.
2. Every nonnegative integer marking satisfying this target conjunction has
   w·m <= B.

Consequently, every prefix m of every target-reaching execution satisfies
w·m <= B: the potential cannot decrease between that prefix and the final target.
This is **not a bound on every originally reachable marking**. Different target
conjunctions can give different bounds and must be processed separately.

For s0 = B - w·m0 >= 0, append a fresh ordinary Petri-net place s with initial
marking s0. Keep every original pre/post arc. For each transition append a pre-arc
on s of weight d_t = w·C_t when d_t > 0; append no slack post-arc. For d_t = 0,
append neither. Extend original target rows with a zero slack coefficient,
preserving their order, bounds and equality flags. No extra target restriction
is necessary. The augmented net maintains the **global invariant in that net**
w·m+s=B, so the slack guard rejects exactly those firings that cross the bound.

Every original target-reaching trace remains enabled in the augmentation: its
next potential is at most B, hence available slack is at least d_t. Conversely,
projecting any augmented target-reaching trace gives an original trace with the
same original marking and target truth. Transition IDs can stay identical.
There is no new solver or changed original token arithmetic in this construction.

## Double-lock example without using names

The inspected double-lock query has initial total token mass 2 and exact target
mass 19. Every original transition preserves total mass or increases it by one.
Thus w=(1,...,1), B=19 is directly certified, using only incidence and target
rows. Slack initially contains **17 tokens**; each population-increasing
transition consumes one. This derives the same useful budget as the local-place
bound 18, without discovering or naming the shared/local partition. The shared
component's invariant mass is one, but that extra fact is unnecessary here.

After the checked target-zero trap projection, the removed coordinates are zero
on successful paths. The all-ones check can be rerun on the projected query;
its initial/target mass remains 2/19. The statically projected net has 65
mass-increasing transitions. The proposed augmentation adds one coordinate and
65 pre-arcs to that net. It excludes irreversible excess population; whether
our searches spend appreciable work there is unknown.

## What already exists

- `capacity.rs` proposes nonincreasing 0/1 weights, with bounds from the **initial**
  marking. `place_bounds.rs` checks nonnegative rational weights against
  w·post <= w·pre and derives global original-net bounds. They use the opposite
  incidence direction from the proposed target-path bound.
- `place_bounds::discover` already uses exact rational-model infrastructure.
  Its search on reversed transitions would propose forward-nondecreasing weights.
  For a verified exact target marking, using that target as the reverse initial
  marking gives the desired candidate bound. Do not use the original initial
  marking for this reversed discovery, or treat its output as an original-net
  global bound.
- `target_zero_trap.rs` proves that some target-zero places must remain empty on
  successful paths. A trap preserves nonemptiness, not necessarily token mass;
  the weighted potential check is different and does not subsume every trap.
- `guided::solve_bounded` uses small ad hoc per-counter caps as underapproximations.
  The checked slack construction preserves all successful traces.
- `count_plan.rs` has arithmetic slack variables, and `complete_target.rs` compiles
  linear target acceptance into point reachability. Neither supplies this
  target-path guard to ordinary-net search. `raw_potential.rs` constructs
  sufficient serial-language nonmembership goals, a different operation.
- I found no existing ordinary-net successful-path slack augmentation in `src/`.
  Existing place-bound discovery and certificate arithmetic should be reused
  where applicable rather than implementing a second optimizer.

## Inference, from cheapest to optional

Start with **one all-ones candidate only**. Validate dimensions and weighted arcs,
then compute every incidence sum exactly. Reject the candidate if any sum is
negative. Extract each supported coordinate's finite upper bound from a unary
negative-coefficient lower inequality or an oriented unary equality. For
`-k*m_i >= b`, k>0, derive `m_i <= floor(-b/k)` using mathematical floor.
For equality, a negative orientation is permitted; optional integer divisibility
checks may detect an impossible equality, but are not required for a sound upper
bound. Select the tightest certified bound U_i and set B=sum_i w_i*U_i.
Retain the row references and check them independently. Split exact equalities
already represented as opposite inequalities need no special inference.

This first attempt costs O(total target coefficients + total arcs), with exact
integer arithmetic, one additional place, and at most one additional arc per
transition. If any required upper bound is missing, skip it. Never substitute
a guessed cap. Enforce a preparation deadline, work budget, and coefficient-size
budget; failure falls back to the unchanged query with remaining time.

Later, only if measurements justify it, propose a small number of sparse weights
via existing reversed-incidence capacity/LP machinery. For exact targets B=w·g
is immediate. For general linear targets, a dual bound certificate can combine
rows a_j·m>=b_j with rational multipliers lambda_j (nonnegative for inequalities,
free for equalities). Check coordinatewise sum_j lambda_j*a_j <= -w. Then
w·m <= U = -sum_j lambda_j*b_j, and integer w·m permits B=floor(U).
The coordinatewise inequality uses m>=0; the flooring step must be explicit.
A floating-point optimum alone is not evidence. General discovery can require
multiple LPs and larger coefficients; it is outside the minimal proposal.

## Proof/checker and failure obligations

A reduction certificate should contain the sparse integer weights, independently
checkable target-bound evidence, and an inner negative proof. Reconstruct the
augmented net and slack initial marking from the original problem; do not trust
serialized maps, d_t, B or augmented input supplied by a solver. Require strict
field sets, sorted unique indices, positive stored weights, valid row references,
and exact arithmetic. Check all original arc multiplicities and all target
coefficients under shared work/deadline limits. Apply the existing nesting limit.

A positive answer needs original-net trace replay and target checking; additionally
checking the reconstructed slack trace is inexpensive and detects integration
errors. A negative answer is valid only after both the reduction certificate and
its inner proof on the reconstructed augmented net verify independently in Rust
and Python. The current policy that an uncertified exhausted search stays unknown
must remain intact. Nested trap/potential/relevance proofs check each inner net
in order. An existing engine must not silently drop the slack guard as redundant
in the original net.

If B-w·m0 < 0, the two checked obligations directly prove this target conjunction
unreachable; emit a separately checked initial-infeasibility certificate, with no
unsigned conversion or fabricated slack marking. A negative B similarly implies
no nonnegative target for nonnegative w. Zero weights everywhere with B>=0 add
nothing and should be skipped; a checked negative bound can still refute the
conjunction. Conflicting target bounds require checked arithmetic evidence, not
an unchecked infeasibility claim.

Compute w·pre, w·post, d_t, B, and w·m0 in BigInt (or checked exact arithmetic
with conservative fallback). Normalize rational weights to integers before
constructing arcs, with size limits on denominator LCM growth. Mathematical
floor is not truncation toward zero for negative rational bounds. The current
`u64` token/arc representation requires exact representability of slack initial
marking and added arc weights; if conversion fails, skip the transform.
Optionally omitting d_t>B transitions is sound but changes transition maps and
proof obligations; keep them or decline the transform in the first version.
Never clamp, saturate or wrap a certificate quantity. Preserve original target
coefficients and append zero, avoiding any new i64 target coefficient requirement.

## Separating example

One place p, initially 0, one source transition `[] -> p`, target p=2. The original
net reaches arbitrarily large p, so no finite original global place bound exists.
The target-path potential w_p=1,B=2 is valid. Add s initially 2 and replace the
source by `s -> p`. All successful original traces are retained, while the
augmented net is bounded by p+s=2. Appending p<=2 only to the target would not
perform this prefix pruning.

The monotonicity check is essential: for initial p=3, a transition `p -> []`, and
target p=2, the initial value exceeds the target bound but the target is reachable.
Here d_t=-1, so the proposed checker must reject the candidate instead of issuing
an initial-infeasibility certificate.

This proposal adds a single checked preprocessing step to the current portfolio.
The all-ones attempt is the appropriate first experiment; broader potential
search, a new engine, and claims of improved performance are not justified yet.
