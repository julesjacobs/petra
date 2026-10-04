# Adaptive control projection for raw SER negatives

**Implement intermediate control projections as a discovery heuristic, preserving both existing certificate formats and both independent checkers. First add phase diagnostics: the saved n4/n5 work-limit results do not identify which discovery stage dominates.** No implementation, build, solver run, remote operation, or reserved-family inspection was performed for this proposal.

The working bridge is pairlocked n3; n4/n5 remain unresolved in the saved component-game comparison. This suggests an experiment, not evidence that projection refinement will solve them. The mechanism is not a complete reachability procedure or an established publication novelty.

## Present implementation and proof boundary

`raw_schema::discover` first discovers at most 256 serial schemas with `max_work/8`, validates/materializes their semilinear subset with another `max_work/8`, gives the latter's remaining allowance plus `max_work/2` to component-invariant discovery, and finally checks the schema wrapper with `max_work/4`. All stages share a deadline. `raw_schemas::discover` returns completed candidates even when its internal search stops early; its returned vector does not identify queue exhaustion, schema cap, work exhaustion, or deadline exhaustion. The existing 256 limit must not be confused with the number of declared or reachable automaton states, or the previously reported prototype endpoint/base/period combinations.

`raw_negative::discover` tries exactly two coordinate sets: the empty set with one eighth of its allowance, then the structural set with seven eighths. Structural coordinates exclude response places, discovered credit places, and places produced by source transitions. These exclusions are heuristics against growing counters; they do not prove that the remaining projection is finite.

For a fixed projection, discovery constructs nodes `(projected marking, serial component)`. Every enabled nonstuttering original transition is an AND obligation; alternative checked component transfers are OR choices. The greatest fixed point already handles these alternatives correctly. A rewrite from greedy transfer selection to a game is therefore not the next missing mechanism.

The existing `raw-component-invariant-v1` checker accepts any sorted unique original-place projection. It reconstructs every projected transition and credited effect, checks the initial node, checks a successor for every enabled nonstuttering transition, and checks exact nonnegative base/period maps. Credits are restricted to completion-zero places, so at completion the credited response vector is the actual response vector. The outer `raw-automaton-invariant-v1` checks explicit paths/cycles and accepting endpoints, establishing that the component language is a subset of the original serial language. Proving inclusion in that subset establishes exclusion-target unreachability.

Consequently, **projection selection and failed-obligation diagnostics are outside the trusted certificate**. Keep the formats, original transition IDs, explicit serial schemas, credit semantics, and Python checker acceptance rules unchanged. Never accept an unfinished game or treat failed discovery as a refutation of the original query.

## Minimal implementation

1. Replace `discover_projection(..., track_control: bool)` with a function taking a sorted original-place slice. Construct the current empty and structural slices through that API first, without changing their schedule; this isolates a behavior-preserving refactor.
2. Separate projection-independent preparation from projected game construction. Prepare credits, initial credit, serial components, sparse credited transition effects, and original incidence once. Preserve the structural candidate pool exactly for the first adaptive version. Cache only completed coefficient/transfer results; an interrupted coefficient search must never cache “no map.”
3. Return an internal discovery status rather than parsing error strings: `Checked(certificate)`, `InitialOutsideComponents`, `LosingGame(obligations)`, `Limited(phase, counters)`, or `Invalid(error)`. Coefficient-dimension and integer-representation limits belong to `Limited`, not `LosingGame`. Discovery status is diagnostic metadata, not certificate content.
4. Add a deterministic refinement loop starting from the empty projection. On a completed losing game, add one omitted candidate coordinate selected from failed closure obligations, then rebuild the projected game. Preserve the same fixed schemas and credits throughout this loop. Stop after a checked proof, no new candidate, a fixed refinement cap, or a resource limit. Keep the full structural projection as an explicitly budgeted fallback.

Initially use the following bounded schedule as a **proposed experimental configuration**, frozen before performance measurement: reserve one eighth of discovery work and wall time for the empty attempt; reserve three eighths for at most eight refinements, dividing the remaining adaptive allowance among the remaining slots; reserve one half for the structural fallback. Reserve a check share inside each attempt rather than giving the discovery graph its entire allowance. Debit full attempt reservations when check-work accounting is unavailable. Unspent adaptive reservations may pass to the structural fallback, but never expand the property deadline. Report every reservation and actual use. This changes the baseline's fallback budget and can regress it; compare with the unchanged baseline under the same whole-query limit. Diagnostic evidence may justify a different preregistered schedule before the comparative run, not retrospective per-query tuning.

Charge shared preparation once before dividing the remaining allowance. Before starting a refinement, compare its reservation with the charged structural lower bound for scanning/reindexing the original incidence; if setup alone cannot fit, skip the remaining adaptive slots and transfer their unused reservation to fallback. This matters for n5's 153,618 transitions: many tiny attempts could spend their entire allowance rebuilding projections. Report that skip explicitly. When isolating the scheduling contribution, use the same shared-preparation refactor for both the empty/structural and adaptive configurations, and retain the frozen original implementation as a separate regression baseline.

Suggested internal interfaces:

```text
PreparedComponents::new(query, schemas/semilinear target, budget)
attempt_projection(prepared, sorted_places, attempt_budget) -> AttemptStatus
choose_coordinate(prepared, sorted_places, bounded_obligations) -> Option<PlaceId>
```

The simplest first implementation rebuilds projected presets, their transition index, and game nodes after every refinement. It may reuse component-transfer and component-period maps because those depend on fixed components and credited effects, not the control coordinates. Do not reuse projected enabledness, successor markings, stutter classification, or winning-node results. A transition that stutters under the old projection can update a newly selected coordinate and require an edge in the new certificate.

## Failed obligations and coordinate choice

Augment greatest-fixed-point elimination with a causal record: when a node loses, retain the transition edge whose final live successor disappeared. An edge with no component transfer is a terminal cause. Retain elimination ranks so successors of a causal edge have lower ranks. Starting from **all losing initial-component candidates**, traverse this finite causal DAG and collect at most 32 terminal obligations in stable transition/component order. Cap both traversal work and stored diagnostic bytes.

Do not simply refine from the first diagnostic `failed_transfer`: it may belong to a component choice irrelevant to every initial winning strategy. Nor is one arbitrary successor path a counterexample: component selection has OR alternatives. The causal DAG explains why every choice on a selected AND obligation loses. It is a discovery explanation, not a concrete original-net execution or a complete noninclusion proof.

For each terminal transition, collect omitted places in its **original preset** that belong to the structural candidate pool. Choose the place with the largest number of collected terminal obligations containing it; break ties by lower original pre/post incidence degree, then original place index. Add just this coordinate. The degree tie-breaker is a cost heuristic, not a finiteness argument. Keep ordering independent of hash-map iteration, source labels, and benchmark names.

If terminal transitions have no eligible omitted preset, inspect presets of transitions on the bounded causal DAG, prioritizing those nearest the terminal obligations, with the same tie-breakers. This allows an earlier spurious enabling step to explain a later failure even when the final transition's guard is already projected. If no candidate remains, record `no_refinement_candidate` and use the scheduled fallback or return unknown.

Adding a coordinate preserves more original enabling information, but **does not establish that an obligation was spurious or that it will disappear**. The failed affine map may reflect missing serial components, an overly broad source component, or limits of the uniform affine-transfer proof language. A replay of a projected path with omitted stutters removed cannot prove spuriousness: omitted transitions may produce tokens in the proposed coordinate. Do not claim an exact concrete counterexample check without including that behavior. The independently checked final invariant remains the sole basis for a negative answer.

If a projected game exhausts resources before reaching a losing fixed point, the minimal version does not invent a causal explanation from its unfinished frontier. Record `Limited` and stop that refinement chain. A later version could use frontier guards as expressly heuristic hints, but it should be a separate ablation. Refining a projection that is already exploding can increase its product further.

## Diagnostics needed before selecting the algorithmic bottleneck

Current Rust final JSON includes `parse_seconds` and `solve_seconds` only if the process returns. `VASS_RAW_NEGATIVE_DIAGNOSTICS` emits setup counts, at most four failed-transfer examples per projection, bounded coefficient-rejection detail, and a game summary only after the greatest fixed point completes. Cached transfer hits clear the rejection details. These diagnostics cannot attribute an interrupted run to schema discovery, projection construction, coefficient search, graph expansion, or checking. The Python worker separately records input-validation, solver, and answer-validation stages and preserves solver stderr, but those stages do not identify Rust internals.

Add opt-in bounded JSONL progress events to a separate diagnostic stream, or retain the current stderr route with explicit framing. Emit a start event before each phase, a finish/error event afterward, and periodic counters every fixed work interval. Flush complete lines. A killed process then leaves a last known phase; absence of a finish event remains censored, never zero work. Keep detailed traces disabled in competitive measurements or enable an identical configuration on both sides.

| Phase | Required evidence |
|---|---|
| Rust parse/validation | start/end times; input byte count; places, transitions and arc count; declared serial states/edges |
| Serial schema discovery | reachable anchors visited, queue high-water mark, completed schemas, skeleton/base candidates, period counts and coefficient-pruning work; explicit stop reason: queue exhausted, schema cap, work, deadline or arithmetic limit |
| Schema validation/materialization | schema/path/cycle counts, generated components/periods, copied net bytes or arc count, elapsed/work and outcome |
| Projection preparation | coordinate list/hash, candidate pool size, projected preset/effect/stutter counts, transition-index construction time/work |
| Projected game expansion | distinct projected markings **separately from** `(marking, component)` nodes; edges/OR targets, queue high-water mark, candidate/enabled transitions, vector coordinates copied/hashed, projected counter overflow |
| Transfer/coefficient search | calls/cache hits, source/destination pairs, negative-residual fast rejects, exact-period hits, recursive coefficient-search nodes, eligible dimension, completed map failures versus resource failures; time/work excluded from graph-administration totals |
| Greatest fixed point | nodes/edges entering, losing/live initial candidates, removed nodes, causal frontier count, elapsed/work |
| Extraction and Rust checking | selected proof nodes/edges, certificate bytes, extraction work, component-check work, outer schema-check work and outcome separately |
| Independent Python checking | existing acceptance result plus elapsed time/work-limit status, within the same outer policy |

Counters distinguish three different problems: many schemas/period decompositions before projection; few projected markings but many component alternatives/expensive transfers; or many projected markings with modest transfer-cache misses. A single aggregate node count cannot distinguish them. Current `coefficients` uses bounded recursive exact enumeration and rejects more than 128 eligible periods; all of those stops must remain distinct from completed map failure. BigInt operations and vector clones are not uniformly represented by current tick counts, so work counts are mechanism diagnostics rather than calibrated instruction counts.

Serial-schema incompleteness must be reported without overinterpretation. Queue exhaustion means the current candidate search finished, not that it constructed the entire automaton Parikh image. Reaching the 256-schema cap means candidates were truncated, not that additional candidates would prove the query. In particular, `InitialOutsideComponents` cannot be repaired by changing control projection with fixed credits/components: the initial credited vector is unchanged. Stop refinement on that outcome and diagnose schema/credit discovery separately.

## Tests and experiment

Before benchmarking, use small generated raw queries with independently enumerable reachable markings. Include: an omitted lock guard creating a failed closure obligation that disappears after refinement; failure caused by an earlier omitted guard; alternative components where an irrelevant losing branch must not drive selection; a shared winning game cycle; completion-zero credits; a transition changing from stutter to nonstutter; weighted guards and projected overflow; and unbounded pending requests that exhaust a projection budget. Pair each safe fixture with an unsafe variant and require the existing Python checker to accept every produced negative. Forge missing projected edges and altered coordinates to confirm checker rejection. Test deterministic coordinate order, cache validity across projections, bounded causal extraction, and unknown on every resource stop.

Run only phase diagnostics first on the existing pairlocked n3/n4/n5 and a validated-observer bridge. Keep their original bytes and frozen configurations. Then compare unchanged empty/structural discovery against adaptive discovery on all 12 diverse sources and all 16 scaling sources, separately identifying the four bridges and preserving pairlocked n6's export failure. Retain unsafe counterparts and prior negative wins, not just n4/n5. Use the existing original-input/independent-check deadline policy for both configurations. Report full source denominators, proof/checking failures, schema counts, projected markings, game nodes, transfer work, certificate size, and peak memory. Any solver-gain claim requires those results; this proposal supplies none.

## Read-source identities

| Source | SHA-256 |
|---|---|
| `src/raw_negative.rs` | `f911f3314ca3b9a3af8f48a4f6c126b13ad2bffc61d4da8760aff7eeb6079213` |
| `src/raw_schema.rs` | `6945f3c32d87c85d4c0981b7c90ad6866769a796007ec72d67ee9c0ba41d2f36` |
| `src/raw_schemas.rs` | `5eec7e97507121bd589873715f805439fb5f481e67af151283639fd933794cc4` |
| `src/raw_invariant.rs` | `dd21a1acae4a35ee893315ac6a6658f5cbe991ca9d2bfced21bd6833209e0413` |
| `scripts/raw_invariant_check.py` | `47ed99a0db558d0262cc0a735293dbb32a118875cf5f093c344d3abcac19ac68` |
| `scripts/raw_schema_check.py` | `03b3c69baac745b73333aeb1d22ae1634182716b88db25931b73bf7b84fef8a5` |
| `scripts/raw_stress_worker.py` | `70b1504f5461e209ad2b85bc186d75c9368c5efbf2b10c2d33fcea4176946d44` |
| `research/benchmark-hardness-next-track.md` | `0d08efa8b18c8e8dbe668fd35a67519cfaf3b2aa511eecd2b2c3c7cec4361dc1` |

Historical coverage and prototype-count statements above come from the saved research reports, not new measurements. Inspection of current code independently establishes the two-projection schedule, proof-interface flexibility, diagnostic gaps, and schema-discovery truncation behavior.
