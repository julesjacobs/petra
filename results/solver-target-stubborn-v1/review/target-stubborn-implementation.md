# Target-directed stubborn-set implementation

The opt-in methods are `relaxed-target-stubborn` and
`portfolio-target-stubborn`. They preserve the existing helpful-only first
third and outer capacity/relevance/causal/local/search schedule. Only the
unrestricted relaxed fallback changes. Default methods, `portfolio-focused`,
`portfolio-stubborn`, state limits and proof formats are unchanged.

At each expansion, target selection chooses the first false conjunct using a
checked i128 dot product with BigInt promotion on overflow. It seeds every
retained transition with the required exact incidence sign, including disabled
transitions. Increasing and decreasing direction indices are cached per
constraint. Index construction has explicit `Building` and `Complete` states;
the builder retains its action/term cursor and exact partial sum across
expansions. Only a complete index can provide seeds. Large nets and even a
single large transition therefore need not restart the same prefix each time
the work budget expires.

Target evaluation, direction-index construction, seeding and weighted closure
share the existing 100,000-work-item budget and global deadline. Incomplete
construction or closure uses full expansion. The shared closure retains all
net-positive producers of one weighted deficient guard for disabled members,
and symmetric disabling dependencies for enabled members. Every enabled closure
member is expanded in the existing helpful-first order. This variant does not
apply target invisibility, seen-successor or periodic-depth provisos. The
existing visibility-based variant still applies its original provisos and work
accounting; exact direction machinery is instantiated only for the new mode.

The preservation argument is in
[target-directed-stubborn-review.md](target-directed-stubborn-review.md).
The retained reduced graph preserves shortest target distance over mathematical
markings. Search ordering is heuristic and does not promise a shortest returned
witness. Finite budgets and u64 counters remain implementation limits. The
existing checked-i128 target acceptance and independent witness checker can
return Unknown on target arithmetic overflow, even when the new selection logic
could evaluate that form exactly. Those components were deliberately unchanged.
All reported positives replay original transitions; empty seeds, exhausted
search, counter overflow and limits still provide no negative certificate.

## Diagnostics

The existing opt-in `VASS_RELAXED_PROFILE` / `VASS_PORTFOLIO_PROFILE` JSON records
on stderr retain their event and counter definitions. A new `target_directed`
boolean identifies the new fallback. `stubborn=true` means either stubborn-set
variant; the helpful-only attempt reports both flags false. `expanded`,
`generated`, `chosen`, `enabled_considered`, `reductions` and full-expansion
reason counters remain available. `full_closure_limit` includes target
evaluation, incomplete sign-index construction, seed or closure budget/deadline
exhaustion. In the target-directed fallback the periodic/visible/seen counters
remain zero. Explicit construction avoids temporary-Drop records; CLI tests
require exactly one record per attempt. Redirect stderr separately from answers.

## Verification

Twelve new private tests cover all improving alternatives, disabled weighted
seeds and all guard producers, symmetric read dependencies, seen/no-op
successors, equality from either side, empty seeds, disabled closures,
partial-index/seeding/closure fallback, counter overflow, and the existing
checked-acceptance overflow limit. Exact marking and incidence sums are tested
with positive partial sums beyond i128 followed by cancelling negative terms;
resumed BigInt sums are checked too. Separate bounded-work regressions require
sign construction to finish across repeated calls for many actions and for one
large action, without admitting a partial seed index.

The independent unsliced BFS differential enumerates all 64 subsets of six
one-token transfer transitions on three places, all six two-token initial
markings, six positive/signed target forms, five bounds and both equality and
inequality: **23,040 queries**. Full and reduced graphs agree on reachability and
exact shortest target distance. Another **240 generated bounded queries** add
weighted transfers, read guards and conjunctive signed/equality targets. Existing
relaxed witness integration tests exercise the new public solver and replay all
reported witnesses. Extended CLI tests cover original PNML/XML capacity on/off,
relevance lifting and independent verification of the resulting proof/witness.

All 22 private tests and the relevant CLI/integration tests passed. The full
suite passed: **371 passed, zero failures, one existing ignored test**.
`cargo clippy --all-targets -- -D warnings` and formatting passed. Existing
vendored Varisat warnings remain; the project has no Clippy warnings.
The release build passed. Release CLI probes returned the expected reachable
and Unknown outcomes, emitted exactly two diagnostics each with the target-mode
flags, and left periodic/visible/seen counters zero. The reachable trace was
independently replayed in Python against the original input arcs and target. Logs are in `results/target-stubborn-validation-v1/`.
No benchmarks, remote actions, competitor code copying, novelty claims or
performance claims are part of this implementation handoff.


Release SHA-256:
`370a39e384f8bae9ead849515c9d844b47bb63b784fd5ba19f334c665f6958e0`.
Final full-suite handle36917, Clippy85182 and release23271 all exited0.
The earlier focused test handles48623,73824,54204,6602,57284 also exited0.
No validation process remains live, and no benchmark was started.
