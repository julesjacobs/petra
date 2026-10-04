# Prepared raw reduction

The raw-potential solver now builds its completion net once, protects every response place, and reuses one reduced net and its lifting recipes across potential goals and direct-search fallback. Each candidate adds one target row and removes it before the next attempt. The original completion net remains immutable.

Reduction eligibility still uses the original incidence relation and ascending place order. Original consumer lists identify demand-source rewrites; original producer lists identify eager-completion rewrites. Eager completion adds outputs only to originally unread places, which cannot become later private sinks. A disposable-place mask replaces repeated target scans. Checked weighted accumulation and the existing 1024 expansion guards are preserved.

An absolute deadline includes reduction preparation, guided search, and lifted replay. Preparation exhaustion discards the partial reduction. No reduction or quotient-exhaustion result establishes raw unreachability: accepted answers still require original trace replay and raw semilinear nonmembership checking.

Protecting every response place can suppress reductions previously allowed for a particular potential. This is intentionally measured as an algorithm variant, rather than treated as a behavior-identical cache. The indexed transformation itself was compared against the former full-scan transformation on 512 deterministic weighted nets with varying initial markings, targets, and protected places, plus multiplicity and overflow cases.

Other tests cover weighted recipe order and shared sink outputs, switching between distinct response goals, interruption at every preparation checkpoint, expired search deadlines, fallback without potential goals, and preservation of unknown after failed goals. The complete Rust suite passed 209 tests with one pre-existing ignored test. A final protected-index error-handling adjustment then passed the five focused reduction tests and all-target clippy. The read-only agent review found no critical issue for validated inputs; its invalid-protected-index finding was fixed before freezing.

Frozen binary and source: `results/solver-prepared-raw-v1`, with hashes in `SHA256SUMS`. The all-source two-repetition ablation is specified in `research/raw-prepared-plan.json`; results are written to `results/raw-stress-prepared-v1`. Compare against the top-32-only variant in `results/raw-stress-sparse-v1`, retaining all 18 selected sources and the six export failures.

This change addresses repeated preparation and deadline accounting. It does not add indexed successor enumeration, incremental scoring, new negative proofs, or a new complete reachability procedure. Those remain separate research and measurement tasks.

## Completed ablation

All 36 planned rows completed. Both the previous and prepared variants independently verify the same five positives in both repetitions; seven valid queries remain unknown and six exports remain unavailable. There are no lost positives or new positives. The eight-cell racy replica's mean observed wall time changes from 1.466 to 1.264 seconds, but monitor timing changes are small or mixed and sampled memory varies substantially. This is not evidence of a broad performance improvement. Exact case-level data are in `research/raw-prepared-comparison.json`.

The next separate ablation combines the completion target into one nonnegative zero-sum equality. Preparation reuse alone has not removed the remaining bottleneck.
