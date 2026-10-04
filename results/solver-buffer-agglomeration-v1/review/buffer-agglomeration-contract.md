# Checked uniform-buffer agglomeration

The implemented rule preserves existential reachability of the complete target conjunction, including signed inequalities and exact equalities. Its proof uses equality of the final queried coordinates, not upward closure of the target. This is a sufficient classical structural rule; it is neither a completeness nor a novelty claim.

## One-step contract

Let p be initially empty and have zero coefficient in every target row. Let P contain every active transition with a post-arc on p, and C every active transition with a pre-arc on p. Both sets must be nonempty and disjoint. Every incident arc must have the same positive weight a. Thus p contains an integer number of packets of size a, each created by one producer and consumed by one consumer.

An **eager** step additionally requires every consumer's complete pre-set to be {(p,a)}, and every consumer output coordinate to have zero coefficient in every target row. A **delayed** step instead requires every producer's complete post-set to be {(p,a)}, and every producer input coordinate to have zero coefficient in every target row. All active incident transitions are checked; a chosen subset is insufficient. Target support is the union of nonzero coefficients over all rows, regardless of signs, equality flags, or bounds.

Remove p and all transitions in P∪C. For each pair (f,c) in P×C, insert a macro representing f followed by c:

- Eager: pre=f.pre; post=(f.post without p)+c.post.
- Delayed: pre=f.pre+(c.pre without p); post=c.post.

Shared coordinates on a merged side use exact addition. No pre/post cancellation is performed: weighted guards and self-loops on other places remain significant. Sums exceeding u64 are rejected rather than wrapped, clamped or saturated. Nonuniform weights and initially nonempty buffers are unsupported.

## Reduced runs expand to original runs

Every retained transition has no arc on p. Start with p=0. In the eager case, the macro's guard is precisely f's guard; f produces a on p, and c requires only that packet. In the delayed case, f produces only that packet; the macro's summed guard ensures that after f consumes its inputs, c's other inputs remain available. This accounts for overlapping inputs exactly. Each pair restores p to zero and has precisely the macro's effect on all other coordinates. Induction expands a reduced run into a run of the pre-step net with identical retained marking. Since p is unqueried, final target truth agrees.

## Original successful runs admit paired runs

Match each consumer occurrence in an original finite run to one distinct earlier producer occurrence. Such an injection exists because p starts empty, all packet weights agree, and the original run never consumes an absent packet. Unmatched producer occurrences account for the final residual packets.

For **eager** reduction, assign each matched producer its matched consumer; assign an arbitrary consumer to each unmatched producer, possible because C is nonempty. Scan the original run: replace each producer by its assigned f;c pair, omit original consumer occurrences, and keep all other occurrences. Immediately before any retained occurrence, the new marking outside p equals the original marking plus the outputs of consumers moved earlier and the additional consumers assigned to unmatched producers. These differences are componentwise nonnegative: every original consumer already passed by the scan has its earlier producer already processed. Retained firings therefore remain enabled. Each new consumer is enabled immediately after its producer. Producer/consumer dependencies through other coordinates cause no problem because consumers only add tokens outside p. At the end, the only additional outside-p tokens are outputs of consumers for unmatched producers. All such coordinates are unqueried, so every queried coordinate is unchanged.

For **delayed** reduction, scan the original run, omit every producer at its original position, replace each consumer occurrence by its matched producer followed by that consumer, and keep other occurrences. Before a retained occurrence, the new marking outside p equals the original marking plus the inputs of original producer occurrences already passed but not yet fired. For a consumer c, this difference includes its matched producer f's entire input multiset. Hence f is enabled, and after f fires the outside-p marking still dominates the original marking before c. The packet just produced enables c's p-input. This also handles overlapping producer/consumer inputs and cyclic dependencies. At the end, the difference consists only of inputs of unmatched, omitted producers; these coordinates are unqueried. Every queried coordinate again agrees exactly.

Both arguments yield a sequence of complete f;c pairs and retained transitions, hence a reduced run. They do not assert that arbitrary prefixes retain the original marking, or that arbitrary target-visible effects can be reordered. For example, eager completion can invalidate an equality on a consumer output, and deletion of a delayed producer can invalidate an equality on its input. Tests include concrete counterexamples to relaxing these restrictions.

## Repeated steps and certificate identity

The certificate schema is exactly:

```json
{"kind":"buffer-agglomeration-v1","steps":[{"place":1,"orientation":"eager"}],"inner":{}}
```

The inner object is a placeholder above; it must contain a separately valid negative proof. Steps are nonempty and refer to stable original place indices. A removed place cannot be selected again. Any valid supplied sequence and either valid orientation are accepted; verification does not assume discovery selected the smallest eligible place or preferred eager orientation.

Original transition IDs remain stable. Removed transitions leave tombstones. Each step appends all macros in ascending producer-ID, then ascending consumer-ID order; macros are never deduplicated. A new macro with stable ID k is named `buffer-macro-k`; original names remain unchanged. Merged sides are sorted by stable original place index, while eager pre-arcs and delayed post-arcs preserve their source order. Final projection retains places in original order and active transitions in ascending stable-ID order, preserving target-row order, bounds and equality flags.

A Rust recipe DAG records each macro's earlier f and c IDs. Expanding a positive answer recursively gives original transition IDs; original-input replay and target checking establish the positive answer. Negative checking independently reconstructs the supplied sequence and validates its inner proof on the exact final net. Each step is an equivalence, so induction establishes equivalence of the whole sequence. Serialized replacement nets, macro arcs, recipes, maps or markings are neither required nor trusted. An unproved reduced exhaustion remains Unknown.

## Limits and independent checks

Stable transition count, including tombstones and macros, is limited to min(1,000,000, max(1024, 4×original transition count)). Cumulative arc count includes all original and appended arcs, including tombstoned transitions, and is limited to 20,000,000. Both implementations reject the original input if it already exceeds the relevant cap. The checker uses incremental incidence maps and explicitly charges work for scans, incidence updates, copying and sorting; it checks limits before large allocations and rejects exhausted work/deadlines. Proof nesting shares the existing outer depth limit and deadline. Python dispatch rejects optimized Python because legacy inner proof checkers use assertions; this new checker's own input validation uses explicit exceptions.

The independent Python checker validates strict field sets, actual integer types, dimensions, index bounds, positive weighted arcs, unique per-side arc indices, u64 initial values and i64 target arithmetic. Reconstruction does not mutate the supplied problem. Tests cover both orientations with checked threshold-closure inner proofs, invalidated inner proofs, exact merge/ordering, multiple stable-ID steps, no deduplication, arithmetic boundaries, cumulative limits, malformed certificates, callback deadlines, mixed nesting, and bounded exhaustive trace checks on cyclic weighted nets. A 512-step generated chain fits an explicit 100,000-unit checker work budget; this is a regression on algorithmic work, not a solver performance measurement.

Static review of the Rust core and Python reconstruction found matching eligibility, arc construction, stable IDs and caps. The 13 focused Python tests pass (`research/buffer-agglomeration-python-tests.log`). Cargo and broader integration validation are coordinated separately. No Linux work or benchmark measurement was performed for this task.
