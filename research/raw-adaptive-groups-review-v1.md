# Bounded-group adaptive projection review v1

Initial read-only review of the pilot proposal, existing adaptive scheduler and `control.rs`, `capacity.rs`, `place_bounds.rs`. No solver/build/test or Linux operation ran. Implementation review is pending the implementer's handoff.

## Proof and support requirements

For each chosen guard `g`, propose a nonnegative potential with `w[g]>0`, verify `w·post <= w·pre` for every original weighted transition, and select its entire positive support. Every projected firing then preserves that inequality because all its weighted coordinates are still present. Finite initial mass bounds every coordinate of the support. Multiple supports can be united as coordinate sets: each individual potential remains an invariant on the union. Arbitrary subsets of a support lose this guarantee.

**The indicator of a union need not itself be nonincreasing.** For transition `q -> p+r`, supports `{p,q}` and `{q,r}` each conserve one token. Starting at `q=1`, their union permits total token mass to increase from 1 to 2, though all coordinates remain bounded. Retain the individual potentials or their sum; do not assign the union a single 0/1 potential or the smallest constituent initial mass.

The existing eligibility filter excludes responses, completion-credit places and source-produced places. It is safe to restrict the proposal domain to eligible places, but support discovery may then fail for a bounded guard. If proposing over all places, retain excluded coordinates when they have positive weight. Never discover a support and then intersect it with eligibility. The guard-selection pool and the support-completion pool are different concepts.

A zero initial mass is a useful proof that all positively weighted coordinates stay zero. Do not reject it by reusing `control::build`, which requires exactly one initial token, exact conservation and one-hot modes. Bounded groups allow nonincrease, arbitrary finite initial mass and multiple occupied places.

Keep original-query invariant/schema checkers unchanged. Boundedness only guides projection choice. Limits or absence of a proposed potential remain Unknown/heuristic failure. Do not omit projected transitions or prune markings by an unchecked potential.

## Minimal discovery recommendation

Use binary variables `x[p]`, force the selected guard's variable to 1, constrain each original transition by `sum(post_weight*x) <= sum(pre_weight*x)`, and minimize `sum(x)`. Extract a finite 0/1 candidate, then validate all original weighted arcs exactly and require the guard in its support. Floating-point feasibility is never sufficient, especially beyond 2^53. Successful exact validation certifies boundedness, not minimum support: claim minimality only with an established optimal solve.

A cheap single-input backward implication proposal, as in `capacity.rs`, can precede MILP; exact validation remains necessary because branching production may invalidate its proposed support. It misses valid supports involving multi-input/weighted transitions and must not decide their absence. Avoid cloning the full raw query into `Problem` merely to call a helper when a direct original-arc scan suffices.

## Resource and fallback requirements

- Charge incidence construction, candidate variables/constraints, exact support validation, initial mass computation, and repeated proposals to the group-selection reservation. Include all of them in its deadline.
- `place_bounds::check` has exact rational arithmetic but no work/deadline interface; calling it directly is not a bounded inner check. `place_bounds::discover` searches globally over coordinates and similarly does not fit a small seed-directed work reservation without adaptation.
- MILP internal work is not measured by the existing structural tick counter. Cap model size and solve wall time, reserve/debit its full proposal allowance, and report that accounting limit honestly. An outer process limit remains necessary for peak memory and overruns.
- Never pass an expired/zero remaining time as an accidental unlimited MILP budget. Check before and after solve; check extraction/validation deadlines too. A timed-out proposal cannot be cached as “no bounded group.”
- Retain successful complete supports; union them monotonically in sorted original-place order. If a chosen guard is already covered, advance deterministically rather than rediscovering an unchanged projection.
- Bounded does not mean small: initial mass `M` across `k` places may still admit combinatorially many projected markings, and component choices multiply game nodes. Preserve graph/resource caps.
- The existing structural fallback has no boundedness certificate. Keep it as an explicitly *uncertified structural fallback*, or separately prove supports covering all its coordinates before calling it bounded. Never transfer a limited full-group attempt directly into a final failure while abandoning its larger fallback reservation.

## Minimal fixtures

1. **Singleton explosion:** `p -> q`, `q -> p`, initial `(1,0)`. Projection `{p}` enables `q -> p` without its omitted guard and grows unboundedly. Complete support `{p,q}` preserves one token. Use a dummy response place with serial language `{0}` so no unrelated response constraint interferes with direct projection tests.
2. **Actual source:** `0 -> p`, initial `p=0`. No nonnegative nonincreasing potential containing `p` exists. Proposal failure is not a reachability verdict.
3. **Weighted arc precision:** `2p -> q`, initial `p=2`; `{p,q}` is nonincreasing, singleton `{q}` is invalid. Also check `2^53 p -> (2^53+1)p`: rounded floating coefficients can look equal, but exact validation must reject singleton `{p}`.
4. **Overlapping supports:** `q -> p+r`, supports `{p,q}` and `{q,r}`. Union selection is valid; union indicator mass 1 is invalid. Check both original inequalities, not a guessed union bound.
5. **Initially empty group:** the two-place cycle with initial `(0,0)` has a valid zero-mass support and exactly one reachable projected marking.
6. **Excluded-support coordinate:** a group requiring a response/credit coordinate must either retain it or be declined under an eligibility-restricted search; filtering it out after proposal must fail exact validation. Example `q -> p`, initial `q=1`, selected guard `p`, with `q` excluded from the usual guard pool.
7. **Limits/forgery:** zero work, expired deadline, proposal timeout, exact-check exhaustion, a candidate omitting its seed, duplicate/unsorted/out-of-range places, and a forged singleton for fixture 1. All malformed/incomplete proposals are rejected or limited; none yields a negative without the unchanged full invariant checker.

## Experimental boundary

The saved pilot reports no coverage gain from singleton refinement and shows projected-game blowup, but bounded groups remain an unmeasured hypothesis. Compare grouped adaptation with both frozen singleton adaptation and structural discovery at the same whole-query wall/memory/work policy and final independent checker limit. Preserve unsafe pairs and all registered source slots. Record group proposal/check cost, support sizes, individual initial masses, union size, repeated setup, graph markings and component-game nodes separately, proof/check cost, and whether the winner was an adaptive attempt or structural fallback. An apparent improvement from a changed cap or changed checker budget is a separate intervention.

## Implementation inspection in progress

The first implementation uses exact bounded breadth-first search over 0/1 support supersets, rather than LP/MILP. For the first transition whose selected post mass exceeds pre mass, it branches on omitted eligible places with negative incidence. Any 0/1 superset repairing that inequality must add at least one such place. Candidates remain sorted and are capped at 32 places and 128 distinct proposals. This avoids a numerical solver and its unmeasured internal work. The caps still make discovery incomplete; absence of a proposal is not absence of a potential, and global support minimality is not claimed.

Read `src/raw_negative_groups.rs` (SHA-256 `3fe92d60c921e74b518be35198223e15ce789362f14ec128a568f53e3a0dbd59`) and scheduler integration in `src/raw_negative_adaptive.rs` (`8a0f85dc83216cf43d13a1e608bb60c1423c0eb680f5fc5a68180fda486f3912`). The exact checker requires the seed, sorted unique eligible support, and verifies all original weighted arcs using BigInt. It accepts zero initial mass. Integration charges support discovery/checking and union sorting to the existing selection reservation before subtracting that work from the projection attempt. It retains full support unions and the corrected structural fallback. No concrete soundness/budget blocker was found in this snapshot.

Seven module fixtures cover conserved swaps, zero/large initial mass, true source/growth, weighted arithmetic beyond floating precision, overlapping supports, malformed/ineligible supports, resource stops and deterministic capped search. Two adaptive integration fixtures cover a singleton explosion repaired by a group and overlapping support unions, including Python certificate checks and unsafe variants. Sources were inspected; tests were not run by this reviewer.

Minor diagnostic limits: accepted support initial mass is computed but discarded, and the scheduler's `no-refinement-candidate` label also covers failure to find a bounded group for its chosen guard. Other guards might have groups. Reports should describe this as stopping the current heuristic chain, not absence of all useful refinement. The structural fallback remains uncertified bounded. These are interpretation/coverage limits, not certificate soundness defects.

Verified unchanged checker hashes in this inspection: Rust component checker `dd21a1acae4a35ee893315ac6a6658f5cbe991ca9d2bfced21bd6833209e0413`; Python component checker `47ed99a0db558d0262cc0a735293dbb32a118875cf5f093c344d3abcac19ac68`; Python schema checker `03b3c69baac745b73333aeb1d22ae1634182716b88db25931b73bf7b84fef8a5`.

## Final handoff inspection

The implementation agent completed its handoff. The groups module hash remains exactly the inspected `3fe92d60c921e74b518be35198223e15ce789362f14ec128a568f53e3a0dbd59`. Re-read the integrated scheduler (now `f4fda10eeb537a2d76d6cd7c04c0f991796ef0207ab7d2b92fc3813fb308e922`), automaton wrapper and CLI routing; no additional blocker found. Grouped and singleton methods remain opt-in and use the same original-query invariant/schema checks.

One concurrent checker implementation change must be distinguished from the earlier byte-identity statement: Python component checker is now `b4cec15ad4f72626082e4dea8423246a349efd0d5412c5a385eeb0a61136c1e5`. Compared it with the frozen diagnostic runner copy. The sole diff replaces the dense duplicate-node identity `(tuple(control), component)` with `(tuple((position,value) for nonzero coordinates), component)`. All controls have already been validated to the same fixed length; hence this sparse identity is injectively equivalent and preserves the duplicate-node acceptance rule. Rust component and Python schema checker hashes remain unchanged. This is static equivalence reasoning, not a rerun of checker tests.

Inspected saved `/tmp/pvass-raw-groups-tests.log` and `/tmp/pvass-raw-groups-cli-tests.log`: 28 raw-negative tests pass, including the seven group-unit/two group-integration fixtures; CLI tests 7 pass, diagnostic tests 3 pass with 1 ignored, schema tests 2 pass. These are implementer-run saved results. No tests, builds or benchmarks were launched by this reviewer. Review complete, with no concrete blocker in the assigned scope and no measured performance claim.
