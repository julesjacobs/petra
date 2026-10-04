# Raw-potential preparation and search audit

Read-only inspection of `raw_potential.rs`, `reduced.rs`, `guided.rs`, `quotient.rs`, `raw_search.rs` and completed `results/raw-stress-v1-pilot`. No code edits, builds or measurements were performed. The top32 candidate-storage repair is separate work and excluded from this recommendation.

## Existing measured evidence

The completed pilot has12validated exports from18planned sources; six frontend failures remain in its denominator. Raw-potential found four independently replayed positive witnesses. The monitor results were:

| Query | Places | Transitions | Pilot outcome | Observed wall | Accepted run states | Trace length |
|---|---:|---:|---|---:|---:|---:|
| monitor_d4_c64 | 528 | 2070 | verified positive | 2.247s | 4612 | 1026 |
| monitor_d4_c128 | 1040 | 4118 | verified positive | 2.514s | 9269 | 2050 |
| monitor_d5_c128 | 1297 | 6426 | verified positive | 2.805s | 14335 | 2562 |
| monitor_d4_c256 | 2064 | 8214 | solver timeout | 8.093s | unavailable | unavailable |
| monitor_d5_c256 | 2577 | 12826 | solver timeout | 8.096s | unavailable | unavailable |
| monitor_d5_c512 | 5137 | 25626 | solver timeout | 8.103s | unavailable | unavailable |

The successful state counts come from solver.stdout and describe the successful guided attempt, not aggregate work across candidate goals. These are single-pass development observations, not repeated speed measurements. Replicas_n8/n10 variants exceeded the sampled memory limit before returning an answer; the separate candidate-allocation diagnosis explains a plausible mechanism but does not profile other costs after that fix.

## Source-established repeated work

- Every potential goal calls `q.net()`, cloning the entire net and building one dense place-length equality per completion place. `reduced::transform` immediately clones that Problem again. Up to32goals repeat this work; fallback raw-search builds/transforms it again.
- `transform_protected` scans every original transition's arcs to find producers and consumers for **each place**. It then scans mutable transitions again to apply a discovered source/sink rewrite. It also repeatedly scans all original inputs to decide whether each sink output is unread. A fixed place-to-transition incidence index can answer all these queries without full-net scans.
- `disposable` traverses all target rows for each place, and scans a dense row when recognizing its single-place zero equality. This target structure is fixed across potentials except for a two-coordinate response inequality.
- `reduced::solve` constructs its reduction **before** starting guided's timeout. Reduction time is therefore outside the supplied per-candidate allowance; raw-potential checks its deadline before the call, but preprocessing can consume the remaining property budget before guided begins a fresh relative timeout. External process deadlines prevent late acceptance in the pilot, but the allocation is misleading and wastes candidate opportunities.
- Guided recomputes active-place discovery using a place × transition-input scan, recomputes each goal's max transition effect, and rebuilds the target projection for every goal. `Projection::new` already contains a simpler linear-arc scan for active places, so guided's separate expensive scan is unnecessary when its token cap is None.
- During exploration every expanded state scans **all transitions**. Each enabled transition clones the entire marking through `Problem::fire`, allocates a complete projection key, and scores all target rows. Even duplicate successors pay for dense clone/key allocation. These are structurally costly for long sparse control paths and replicated nets, independently of candidate generation.

These costs are proven by control flow, but their relative wall-time shares have not been measured. No claim is made that reduction is the dominant remaining bottleneck.

## Minimal next improvement: prepare one protected reduced net

Prepare `q.net()` once, build one incidence index, and call `transform_protected(base, all_response_places)` once. Protect **all** response coordinates, rather than only the current potential's one/two coordinates. Keep the resulting net and original-transition lifting recipes for every potential and the eventual raw-search fallback. Temporarily append/replace the potential target row in this one owned net; avoid a full Problem clone per goal.

The protection requirement matters: the current target-sensitive reduction can eliminate places that are irrelevant to one goal but relevant to another. Blindly caching the first candidate's transformed net is unjustified. Protecting the union of candidate supports (all response places is the simple conservative choice) makes disposability independent of candidate choice. It may suppress some reductions compared with the old per-goal transformation, so benchmark it as a real variant rather than assuming identical search behavior.

The incidence index stores original producer/consumer transition lists per place and a Boolean `read_by_transition` array. Reuse **original** incidence when deciding reductions, matching the existing algorithm; using progressively rewritten incidence could change rewrite eligibility/recipes. Apply edits only to listed consumers/producers in the mutable net. Protected lookup should be a Boolean place mask. Recognize completion-only target rows once instead of repeatedly scanning dense target rows. Preserve current multiplicity/overflow/1024recipe guards.

Use one absolute deadline throughout preparation and search. Charge preparation to the property once and pass only remaining time to each goal. Add periodic deadline checks during index construction/transformation and return unknown on exhaustion. Do not start a fresh full relative budget after preparation. This fixes a concrete scheduling defect while eliminating repeated work.

Expose a small prepared interface (`net`, `recipes`, static incidence) shared by reduced-guided and raw-search, with one lift-and-check helper. Positive acceptance must still lift the trace, replay it on the original completion net, and call `q.accepts` on the replayed marking. Only the final original witness/nonmembership check is trusted. No new negative answer is authorized by preparation or quotient exhaustion.

## Follow-up after measuring preparation

For long monitors, the next targeted improvement should be incidence-driven successor enumeration. Assign each transition one fixed preplace as an anchor, plus a separate source-transition list. For a marking, visit transitions anchored at marked places and check their **complete weighted preset** exactly; transitions with empty presets are always considered. Every enabled transition is considered because its anchor must have a positive marking. Choosing one anchor avoids duplicate visits without per-expansion HashSet allocations. Use a sparse maintained list of marked anchor places, or a place scan initially; the latter is still often much smaller than the full transition scan.

This is a general search optimization and preserves witnesses; it does not rely on monitor names or source generator structure. For full reuse, compile this index once for the prepared net. It should be measured independently from reduction caching so gains are attributable.

Later, incrementally score only target rows touched by a fired transition. The completion target contains many single-coordinate zero equalities; rescoring every unchanged equality per successor is unnecessary. Store exact unsatisfied-row counts for acceptance and keep heuristic arithmetic separate. Saturated heuristic sums cannot be blindly subtracted when updating; recompute on saturation or use checked unsaturated totals. Avoid adding dense per-goal-value vectors to every search node, which would replace one memory problem with another.

Dense marking/projection-key allocation can then be reduced using a reusable successor scratch buffer: apply/check a transition, compute/look up its key, and clone only for genuinely new states. Preserve full concrete markings for witness replay. A quotient collision must not invent reachability; original replay remains mandatory.

## Verification and ablations

Before timed comparisons, test index-based reduction against current transformation on small nets with sources, private sinks, weighted arcs, overlaps and protected goal coordinates; compare lifted traces on the original net. Include two potentials that mention different response places to catch unsound first-goal caching. Inject a clock or bounded transformation work limit to verify preparation consumes the shared deadline.

For successor indexing, compare enabled transition sets and successor markings with `Problem::fire` on random small weighted nets, including empty presets, multi-input transitions, zero markings and shared anchors. Validate original witnesses on every accepted result.

Freeze distinct variants: top32 fix alone; prepared reduction/index; prepared reduction plus anchored successors. Run all18planned raw sources with the existing10s/2GiB process envelope and report all frontend failures, unknowns, resource failures and independently checked witnesses. Do not count result unions as a deployed portfolio. Record preparation time, candidate count/attempt count, expanded states and transition enabling checks to distinguish setup gains from search gains. Only after those measurements should dense scoring/allocation changes be added.
