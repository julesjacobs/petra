# Target-directed stubborn reduction: coordinator review

Reviewed the in-progress implementation in `src/relaxed.rs`, dispatch in
`src/main.rs`, and private tests in `src/relaxed_stubborn_tests.rs`. Final full-suite,
Clippy, release, format and handoff evidence remain pending; no performance claim.

The selector evaluates a false conjunct with checked i128 arithmetic and BigInt
promotion. Its exact direction cache covers all retained actions, including
currently disabled actions, and keeps both positive and negative alternatives.
Only `DirectionCache::Complete` exposes seeds. The Building state retains the
exact sum plus action/term cursors, advancing a term only after incorporating it;
completed actions enter a direction list exactly once. Deadline/work exhaustion
returns full expansion. This fixes the reviewed repeated-prefix-construction
problem without using incomplete seed sets.

The shared closure retains weighted guard tests, every positive net producer of
one deficient guard for disabled members, and both reader/consumer dependency
directions for enabled members. Target mode disables the old visibility condition
and uses neither discovery-depth nor seen-state provisos. Selection is intersected
with the entire enabled order, not only helpful transitions. Marking deduplication
and the existing periodic FIFO scheduler remain in place. Exhaustion never emits
an unchecked negative result.

The off path retains lazy helpful-first expansion. The target method runs the
same helpful first third, then reduces only unrestricted fallback. CLI dispatch
uses the same relevance/capacity processing, causal/local phases, state limits
and remaining-budget schedule as the existing focused/stubborn portfolios.
The existing invisible reduction retains its original seed, visibility, periodic,
seen-successor and overflow behavior after closure refactoring.

Private differential tests use an unsliced graph and independent `Problem::fire`
BFS, preventing relevance slicing from hiding a selector bug. They compare
reachability and shortest distance over 23,040 exhaustive bounded queries and
240 generated weighted/read-arc conjunctive queries. Separate tests exercise
all improving seeds, disabled weighted enabling, symmetric reader conflicts,
equality directions, beyond-i128 cancellation, resource fallback, cache progress,
and token/acceptance overflow. Test execution status belongs in the agent's final
handoff, not this source review.

Remaining arithmetic boundary: whole-engine target acceptance and original
witness replay use checked i128 and may return Unknown on overflow, even when
selector arithmetic can evaluate the target. u64 markings also remain bounded
machine representations. These are conservative incompleteness limits, and the
new selector does not establish a complete mathematical reachability procedure.

No additional soundness issue was found in this review. Registration/freeze,
original-input smoke, full development comparison, preserved v1 repeats, and
competitor/held-out evidence are still required. Related property-directed
stubborn sets are already implemented in VerifyPN; no novelty claim is justified.

Final handoff verified: full-suite371/0/1, formatting, Clippy, release and CLI
checks pass. Agent confirmed all validation sessions terminal and released the
local window; coordinator inspected final logs and diagnostic records. Frozen
binary/source and pre-freeze review copies are in `results/solver-target-stubborn-v1`.
No remaining code-review blocker. Benchmark smoke/screen are registered, unlaunched.
