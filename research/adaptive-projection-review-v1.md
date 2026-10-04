# Adaptive projection review v1

Scope: static review of `research/raw-adaptive-projection-plan.md`, the existing `src/raw_negative.rs`, Rust/Python component checkers and schema wrapper. No builds, solver runs, tests, remote calls or checker edits. The adaptive implementation was not yet present at the first inspection; conclusions below concern the design and required implementation checks. This is not a completed implementation approval.

## Soundness boundary

The design is sound as a discovery heuristic if every negative still passes the existing original-query certificate checks. An invariant node covers a projected marking and a complete credited linear component. Every enabled original transition that changes either projection or credited response must have an affine successor map into one invariant node. The checker reconstructs weighted presets and effects from original transition IDs. A stuttering transition preserves both tracked quantities. At completed markings all credited completion-zero places vanish, so the credited response equals the actual response. The automaton wrapper separately checks that each component belongs to an explicitly witnessed serial path schema. Adaptive coordinate choice needs no new trusted certificate rule.

Current Rust/Python checkers enforce that boundary, including missing edges, exact projected successors, initial membership, original weighted presets, and base/period maps. Keep their formats and acceptance conditions unchanged. A losing abstraction, exhausted search, missing schema, or unrepresentable coefficient proves no property of concrete reachability; externally these remain Unknown unless another method supplies a checked proof/witness.

## Implementation gates

1. **Preserve OR choices and all initial candidates.** A node loses only when one AND obligation has no live OR successor. A dead alternative beside a winning alternative must not drive refinement. For a completed losing game, a causal edge must account for every OR target having already lost; ranks must decrease along the chosen explanation. A bounded 32-terminal traversal can be a partial explanation: record truncation, and never present it as a complete concrete counterexample.
2. **Invalidate projection-dependent data.** Rebuild presets, transition indices, successor markings, stutter classification and game outcomes after every added place. Sorted original-place IDs are not positions in the projected vector. Sharing complete component-transfer and period maps is valid only while schemas/components and credit effects remain fixed. Never cache an interrupted transfer enumeration as its partial set of choices or as an empty result.
3. **Preserve weighted guards even with zero delta.** A self-loop `2p -> 2p+r` retains the preset weight 2. Incidence/delta alone cannot reconstruct enabledness. Omitted presets may weaken guards, giving an overapproximation; inventing a stronger guard could incorrectly remove a required transition. The final unchanged checker must independently catch the latter.
4. **Keep mathematical failure separate from resource limits.** Work/deadline/eligible-dimension/u64 stops must return Limited, not completed no-map, completed losing game, or initial-outside-components. InitialOutsideComponents requires completed membership checks for all candidate components; an interrupted alternative prevents that conclusion. A limit may end the refinement chain and invoke a separately reserved fallback, but cannot justify causal refinement as though the graph were complete.
5. **Account for repeated attempts and checks.** Charge shared preparation once. Reserve/check each attempt inside the original total work and deadline; do not grant the full allowance afresh per refinement. If checker consumption is unavailable, debit its full reservation. Report skipped attempts whose setup cannot fit. Preserve the fixed component/schema set throughout one adaptive experiment, or label that additional change separately.

## Minimal fixtures

All net fixtures use ordinary places, `zero_places=[]`, one response place `r`, and serial language `{0}` (one component with empty base and no periods), unless stated otherwise. Names below are explanatory; heuristic choices must not inspect names.

### A. OR causality and winning cycles

Use a tiny internal game, avoiding affine-map construction noise:

- Node 0 has one transition obligation with targets `{1,2}`.
- Node 1 has a transition obligation with no targets.
- Node 2 has a self-cycle.

Nodes 0 and 2 must remain live; the empty option at node 1 supplies no refinement reason for node 0. Add a second obligation at node 0 pointing only to node 1: node 0 must now lose despite its first obligation still having a live target. Replace node 2's self-cycle with its own empty obligation: a causal explanation of the original single obligation must include losses of both targets. Finally use initial candidates `{1,2}`: the winning candidate 2 is sufficient. This catches arbitrary-first-successor and arbitrary-first-initial-component errors.

### B. Weighted guard with zero control delta

Places `(p,r)`, initial `(1,0)`, transition `2p -> 2p+r`. The original net cannot move and is safe. Empty projection invents a response-producing obligation; projection `{p}` disables it and admits a one-node, edge-free certificate. Set initial `p=2`: one step reaches `r=1`, so the same edge-free proof must fail with a missing enabled edge. This catches loss of guard weight and use of delta as a preset. Forge a proof with initial controller 1 for the unsafe net: initial-controller validation must reject it too.

### C. Stutter becomes nonstutter

Places `(p,q,r)`, initial `(1,0,0)`, only transition `move: p -> q`. Under the empty projection it is a stutter and a single-node edge-free proof is valid. Under projection `{p}`, the proof requires two nodes with controls 1 and 0, and a `move` edge from the first to the second. Reuse the coarse stutter cache or omit that edge: the unchanged checker must reject it. Test the explicit projection attempt API here; the full adaptive solver can correctly finish at the coarse proof without refining.

Unsafe counterpart: add `emit: q -> q+r`. After `move,emit`, the target is reached. No projected proof may omit the newly relevant `move` edge to avoid the response obligation. The `{q}` projection also requires correct post-coordinate mapping.

### D. Earlier omitted guard, terminal already projected

Places `(a,p,s,r)`, initial `(1,0,0,0)`. Transitions `enable: a+p -> p+s` and `emit: s -> s+r`. Start the attempt with projection `{a,s}`. It invents one `enable`, consuming the selected one-shot token `a`, then reaches a failing `emit` obligation, whose only original preset is the already-selected `s`. Refinement must inspect an earlier causal edge and select `p`, yielding a closed initial node under `{a,p,s}`. With initial `p=1`, the concrete sequence `enable,emit` is unsafe. The selected one-shot token is necessary to keep this projected game finite; without it, repeated spurious `enable` transitions can exhaust expansion before a losing fixed point exists. This catches refinement restricted to terminal presets and replay claims that ignore omitted enabling behavior. A bounded causal traversal may instead decline to refine; that is Unknown, not unsoundness.

### E. Resource stop is not completed failure

- On fixture B, zero work or an expired deadline must return Limited/Unknown; no losing-game explanation may be emitted from an unfinished graph.
- One response `r`, initial `r=2`, no transitions, component base zero with 129 copies of period `r`. Membership is trivial mathematically, but current coefficient search sees 129 eligible periods because target `2r` is not an exact single period. The dimension cap must be Limited, never InitialOutsideComponents or no-map.
- Unit-test a coefficient target larger than u64 against period `r`: the representational stop must be Limited, even though the natural-number coefficient exists. A net variant can obtain such a credited target from a completion-zero place and a weight-2 credit.
- Interrupt transfer enumeration after a completed destination but before later destinations. A later generous call on the same prepared cache must discover every completed valid option, rather than reuse a truncated vector or empty cache entry.
- Supply a valid certificate but zero independent checker work. The overall answer remains Unknown/verification-limited. Discovery success alone must not bypass either checker.

Fixture B and C certificates are hand-derived above, not executed. Integrate them with the existing independent Python checker and reject forged missing edges, changed coordinate IDs, incorrect initial controllers, and weighted-guard omissions. The existing reset/use component-choice fixture remains a useful integration regression alongside the isolated game tests.

## Experiment separating adaptation from a larger cap

Saved `research/raw-phase-diagnostics-v1-analysis.json` reports n4 pairlocked as Unknown/work-limit at baseline work and verified-negative at expanded work; n5 remains Unknown/work-limit. These are historical saved classifications read during this review, not independently rerun certificates. Thus solving n4 with the adaptive candidate is not by itself evidence for the adaptive mechanism.

Register these configurations before the comparative run:

1. Frozen original empty/structural implementation, original work limit.
2. Shared-preparation refactor, unchanged empty/structural schedule, same total limit.
3. Shared preparation plus adaptive schedule, same total limit.
4. Baseline and adaptive at a prespecified larger total work limit, using the same outer wall/memory policy. This establishes whether the practical gain is merely accessible by raising the cap.

Keep schemas, credits, target/input bytes, final checker budgets and diagnostic enablement matched within each ablation. If the current harness couples checker work to `--max-states`, state both limits explicitly and compare solver discovery and independent verification outcomes separately. Increased-budget rows are a separate intervention; do not substitute them into the equal-budget result table. Time each method including original input and independent checking, retain Unknowns/export failures, and rerun enough repetitions to expose schedule instability.

Use all 12 diverse +16 scaling source slots, identify the four bridges and 24 unique source programs, and preserve pairlocked n6's unavailable export. Keep unsafe pairs and prior solved negatives. Reserved families stay untouched. Report winning attempts and coordinates, reservations/charged work, completed versus limited attempts, schema count, projected markings separately from component-game nodes, transfer work/cache reuse, certificate size/checking and memory. Censored phase records cannot be treated as zero time or evidence of phase completion.

A gain of (2) over (1) supports shared preparation; (3) over (2) under matched limits supports adaptation; a gain only at larger limits supports a budget change. No gain or novelty claim is established by this review.

## Implementation coordination

The implementation agent confirmed the intended opt-in API `discover_adaptive(q, deadline, max_work)`, preservation of existing `discover`, explicit sorted-place projection helper, GFP loss causes/ranks, all-target causal traversal, and the 1/8 +3/8 +1/2 schedule. These are stated implementation intentions, not code verified in this review. The agent was notified of the fixture requirements and of the need to separate repeated setup/check costs from adaptive benefit.

## First code follow-up: one fallback blocker

The opt-in module appeared during follow-up and was read without execution. `src/raw_negative_adaptive.rs::discover_adaptive` initially returned immediately after a refinement whenever `selected == prepared.eligible`, using `return last.unwrap()?.certificate()`. This also returned resource errors and abandoned the structural fallback reservation. With one eligible coordinate, the first refinement is already the full structural projection but gets only roughly 3/64 of remaining work before its check share, whereas at least half remains reserved for fallback. A limited full-projection attempt must still be retried under the fallback reservation. A checked proof may return immediately; a completed losing full-projection game can stop without retry, provided the result remains Unknown. Reported directly to the implementer and root before execution.

Add a scheduler regression where the first full-projection attempt exhausts its small reservation and the reserved fallback succeeds (prefer an injected attempt outcome/budget fixture over wall-clock sleeps). Assert both the fallback invocation and that total reservations remain within the whole allowance.

The inspected code rebuilds credits, components, projected transitions and transfer caches per attempt. Its `Preparation` caches only coordinate eligibility, incidence degree and a setup lower bound. This is a narrower implementation than the plan's shared component preparation; reports must disclose repeated setup. The suitable immediate equal-budget comparator is the unchanged discovery path, and any future shared-preparation contribution needs its own ablation.

The remaining reviewed code preserves exact sorted original-place projections, all losing initial candidates, all OR targets along causal edges, rank decrease checks, bounded stored obligations with truncation counters, completed-only maps within each attempt, and final unchanged Rust checking. Errors are kept separate from `Attempt::Losing`/`InitialOutside`, though `limited-or-invalid` does not yet provide the proposed typed limit classification. No executed validation or final implementation approval is claimed.

## Fallback fix inspected

The implementer changed the full-projection branch to `break`; the following match accepts checked proofs and otherwise reaches `fallback_work += unused` and the structural attempt. Static inspection confirms the reported fallback bug is fixed. Nine new tests are present covering weighted guards, stutter edge regeneration, earlier guards, OR causality, bounded ordering, resource stops, malformed projections and credits; they were read, not executed. The specific small-reservation/full-projection-limit/fallback-success regression is not among those nine tests and remains recommended before treating this scheduling bug as regression-protected. No remaining concrete soundness blocker was found in the inspected adaptive discovery code; actual test/build and certificate-validation results remain the parent/implementer's responsibility.

## Regression and saved validation follow-up

Inspected the added `limited_full_projection_refinement_keeps_the_structural_fallback` fixture: initial `p=12`, decrement transition `p -> 0`, and blocked response transition `13p -> 13p+r`. The explicit full-projection attempt fails at 100 work; adaptive discovery at 2,000 work must yield 13 certificate nodes accepted by the Python checker. This is a finite deterministic fixture exercising a limited first refinement and a successful larger fallback. The previous missing-regression recommendation is now addressed.

The saved `research/raw-adaptive-library-tests.log` contains successful records for all ten adaptive tests and a 193-passed library summary. This is inspection of parent-run validation output, not an independent rerun. No benchmark effectiveness result follows from these tests.
