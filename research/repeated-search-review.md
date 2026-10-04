# Independent repeated-firing review

Reviewed `src/repeat_fire.rs`, `src/relaxed.rs`, CLI method wiring, and
`tests/repeated_search.rs`. All four files exactly match the source archive in
`results/solver-repeated-search-v1`. Read the saved helper-test log and contract;
did not run Cargo, solvers, benchmarks, or access Linux. Full regression evidence
is being audited separately.

## Findings

No blocking correctness issue found. One operational limitation deserves explicit
tracking: `src/relaxed.rs:987` expands the entire witness and calls
`Problem::check_witness` without a deadline check. Repeated edges make a long
witness reachable after very little search, so direct library calls can spend
substantial time replaying after their requested timeout and return a late
positive answer. Replay visits every place for every firing. The existing
original-input scheduler censors late outcomes, and the strict outer benchmark
deadline covers replay and serialization, so this does not invalidate the
registered timed experiments. This behavior also existed in single-step search,
but repeated firing makes it easier to trigger. Before advertising a strict
library timeout, pass a deadline through witness expansion and replay and check
it periodically. A final deadline check alone prevents a late positive answer
but does not bound completion latency.

The one-million-firing constant is an added-edge limit, not a global trace cap.
Every repeated edge ends at depth at most one million; later single steps can
continue beyond that depth. Thus witness length is bounded approximately by one
million plus the state cap, rather than one million alone. The contract states
this distinction accurately. Retaining single steps also does not preserve
success under a fixed state budget: added states can consume that budget first.
Neither behavior is a soundness defect.

## Soundness assessment

- For a decreasing place, the sparse bound checks the full initial input guard
  and limits repetitions to `1 + (tokens - input) / decrease`. This preserves
  every prefix even when the transition has a self-loop. Zero-effect self-loop
  guards are retained. The additional final nonnegativity bound is conservative
  and redundant for valid decreasing Petri-net arcs.
- Positive effects are bounded by available `u64` headroom. Sparse effects are
  unique, sorted, and differences of validated `u64` arcs. The seemingly
  unchecked `1 + quotient` cannot overflow under that contract: a decreasing
  effect necessarily has a positive input weight. `fire_many` checks repetition
  bounds again before applying effects. Its arithmetic stays representable for
  accepted repeated successors; a single-step effect plus a `u64` marking fits
  `i128`.
- Dense `fire` distinguishes an earlier disabled prefix from an earlier
  overflowing prefix, matching ordinary firing. Zero repetitions validate the
  input and return the original marking. The saved helper suite covers both
  failure orders and extreme arc values. Its small exhaustive loop represents
  73,728 marking/repetition combinations (`4^4 * 6^2 * 8`).
- Target crossing counts are only heuristics. Their effect sums can saturate,
  and target-value summation can decline a candidate on overflow, but neither
  outcome creates a negative answer. A selected repetition must pass the exact
  guard/representation bound, and the final ordinary witness is replayed on
  the original problem. An omitted-place overflow after relevance projection
  likewise causes replay failure and Unknown, not a false positive.
- Ancestry stores immutable parent indices, original transition indices, and
  repetition counts. Expanding identical-transition runs while walking backward
  and reversing the complete vector restores the correct forward order. Each
  repeated count is at most one million, so the `usize` conversion is safe on
  supported 32-bit and 64-bit targets. Ordinary replay checks every prefix and
  the final target; existing relevance and buffer lifting remain in force.
- Existing entry points pass `batched=false`; only `relaxed-batched` and
  `portfolio-batched` enable repeated successors. The CLI default remains
  `portfolio-v2`. Existing search semantics retain single-step successors,
  though shared-loop overhead and ancestry storage change. The new portfolio
  uses the same capacity and relevance preparation as `portfolio-focused`.
  The new positive search returns Unknown on exhaustion or limits. Negative
  answers from the surrounding portfolio still require its existing proofs.

The implementation is classical finite repeated firing integrated into a
positive-search portfolio. It supplies no completeness or novelty result.
The Circadian success is a selected development result; broad performance and
competition claims depend on the separately audited experiments.
