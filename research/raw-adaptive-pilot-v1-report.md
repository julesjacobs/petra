# Adaptive projection pilot: no coverage improvement

All 16 registered rows completed. At the standard work limit both methods
prove two of four queries; at the expanded limit both prove three of four.
All ten definitive answers passed the existing independent checker. No verdict
disagreement occurred. The default solver has not been replaced by adaptation.

| Work tier | Baseline negative | Adaptive negative | Remaining case(s) |
|---|---:|---:|---|
| 20 million discovery/checker work | 2/4 | 2/4 | pairlocked n4 and n5 |
| 2 billion discovery/checker work | 3/4 | 3/4 | pairlocked n5 |

These are local diagnostic runs at a 30-second input/check-inclusive deadline,
sampled 2 GiB RSS, one repetition, and the same frozen binary. Both tiers also
increase independent checker work, so the tier comparison is a joint resource
intervention. Detailed logging adds overhead; no stable speed comparison follows.
Original schema construction and final checker rules are identical across
methods. Adaptive preparation is repeated and charged per attempt; there is no
shared-preparation implementation or claim.

The failed hypothesis is informative. With expanded work, n3's first
single-coordinate projection reached 49,576 game nodes before its slice deadline.
Its structural fallback used 756 nodes and produced the accepted proof. n4 first
lost a two-node game, then its two-coordinate projection reached 9,748 nodes
before its slice deadline; structural fallback again supplied the proof. Thus
adding individual coordinates does not ensure a smaller or finite projected
game. Dropping the other coordinates of a bounded control component can permit
unbounded token growth in the abstraction.

n5's baseline hit the sampled memory limit at about 2.06 GiB. The adaptive run
returned Unknown at its work limit, with about 1.89 GiB peak RSS. Neither supplied
a proof; this is not an improvement in solved coverage. Some adaptive logs hit
the fixed process-wide record cap, and their unfinished phases remain censored.
The earlier complete diagnostic records remain available separately.

The candidate implements causal refinement from completed losing AND/OR games,
covering every alternative on a causal edge and every losing initial choice.
It preserves weighted presets, rebuilds projection-dependent state, retains
existing certificate formats, and uses checked certificates as the sole basis
for negative answers. Resource failures return Unknown. The fallback budget bug
found in review was fixed and has a dedicated regression test.

Validation before freeze: 193 library tests, seven raw CLI tests, three diagnostic
integration tests, two schema integration tests, and 20 Python harness tests.
Formatting, Clippy and release builds pass; existing vendor warnings remain.
The freezer verifies stable source hashes across its build and archived contents.

Artifacts: `raw-adaptive-pilot-v1-plan.json`,
`raw-adaptive-pilot-v1-analysis.json`, `results/solver-raw-adaptive-v1`, and
`adaptive-projection-review-v1.md`. Candidate binary SHA-256:
`eabee00a8b6e0f096b0c8716c18cc14e416e6995eb57dcf0a92bf2f573e95457`.

## Next hypothesis: bounded groups of control places

Before refining from a chosen guard, find a small nonnegative place potential
whose support contains that guard. Require the complete support in the
projection. Verify the potential on original weighted arcs: for every transition,
the weighted post-sum must not exceed the weighted pre-sum. Finite initial mass
then bounds each positive-weight coordinate. A union of such supports remains
bounded because all individual potential inequalities are preserved by its
projected transitions. Merely observing bounded markings is insufficient.

A bounded, time-limited LP/MILP can propose a support; exact arithmetic must
validate it. Begin with 0/1 potentials and minimal supports, with no model-name
rules. Failure to find a potential is only heuristic failure. Preserve a bounded
fallback, and compare against both frozen single-coordinate adaptation and the
structural baseline at equal wall, memory and work limits. Group preparation
costs must be included, and repeated preparation must remain visible. The
existing original-query certificate checker remains unchanged.

Required fixtures include a two-place conserved token whose singleton projection
is unbounded, an actually unbounded source place with no bounded support, weighted
arcs, overlapping certified supports, an initially empty support, time/work
exhaustion during proposal, and a forged potential rejected by exact checking.
This is a proposal. No bounded-group implementation, measured gain or novelty
claim exists yet.
