# Implicit stutters in finite token-flow refinement

Status: implementation and validation in progress. This is a representation and
optimization proposal for the existing relaxation; novelty and competitive benefit
are not established.

## Why change the representation?

The finite projection retains original transitions at every enabled control mode.
A transition is a stutter when it leaves all selected coordinates unchanged. It
may still change unselected places. Large DLC nets necessarily have tens of
thousands of such edges even with only one control mode, exceeding the explicit
graph's 8,192-edge limit before numerical solving starts.

Canonical modes can be discovered using all original transitions while storing
only mode-changing edges. Stutter eligibility is reconstructed from selected
guards in each mode. Original transition identities remain available for witness
realization; sharing a projected effect does not justify merging their guards.

## Why moments on stutters can be eliminated

For an edge e at mode q, firing count x_e and original place effect Δ_e,p, a
source moment appears with opposite signs at the source and target. When both
are q, these terms cancel. The remaining contribution is Δ_e,p x_e. Its source
moment interval is nonempty because the relaxation uses lower ≤ upper; an
unbounded upper also permits the lower endpoint.

Consequently, a stutter column has original state-equation coefficients, zero
mode-balance coefficients, and coefficient −Δ_e,p in a cut for place p exactly
when q belongs to that cut. Its own source moment contributes no additional flow
restriction. Stutters with omitted count zero contribute zero demand and need no
edge in the flow separator. **This does not apply to mode-changing edges:** an
unbounded source moment can remain nonzero when the firing count is zero.

## Column generation and proof obligations

The numerical master begins with all mode-changing columns and final-marking
variables. If it yields a feasible model, omitted counts are zero. Cuts derived
from that model remain valid for the full relaxation; subsequent masters must
include each cut's coefficient for every activated column.

If the restricted master yields a Farkas vector λ, it is only a candidate proof.
For rows Ax ≥ b with nonnegative variables, acceptance requires λ ≥ 0,
λᵀb > 0, and λᵀA_j ≤ 0 for every original column j. A streaming scan finds
omitted stutters with positive coefficients and adds a bounded batch. An empty
scan proves the full column condition. Resource exhaustion returns unknown.

The proof stores checked bounds, selected coordinates and one cut/multiplier
obligation per terminal mode. It stores no active-column identities. Both checkers
reconstruct modes and columns from the original net. Row order is independent of
the active set: doubled marking equations, doubled selected terminal equations,
target rows, doubled mode balances, then cuts. Positive answers still require
original-transition replay.

## Evaluation boundary

Compare against the explicit formulation on small weighted nets, reject a
restricted proof invalidated by an omitted producing stutter, retain zero-count
unbounded mode-changing edges, and check generated certificates independently.
Then freeze binaries and measure full development comparisons and a representative
DLC diagnostic. Record fixed edges, total implicit stutters, active columns,
pricing rounds, checking costs and coverage. Pricing may activate every stutter;
fewer stored columns alone is not evidence of faster solving.
