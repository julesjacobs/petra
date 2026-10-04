# Balanced raw portfolio and representation review

Static review only. No builds, tests, solver runs, runner edits, or remote operations were performed. The cohort run was left alone. Reported n5 acceptance comes from `research/raw-checker-sparse-identity-v1-report.md`, not independent rerunning in this review.

## Findings

No correctness blocker found in the inspected changes. No mandatory representation fix is needed before the scheduled validation.

- Rc control interning uses full slice equality/hash, not pointer identity or a lossy digest. Immutable shared controls retain component IDs in game keys, and transition firing copies before mutation. Certificate extraction restores dense vectors. This preserves the game and proof semantics. Interning adds charged work, so a fixed-work comparison is not exclusively a memory-layout ablation.
- Typed streaming output preserves the existing certificate shape. Negative results keep `Outcome.proof` empty and place their typed certificate in the outer `proof`; current positive paths carry no proof. There is no duplicate proof key on current paths. `solve_seconds` excludes serialization; use worker end-to-end time for comparisons.
- Sparse Python duplicate keys are injective after validation fixes vector dimension and requires exact nonnegative u64 integers. Nonzero position/value pairs plus component identity preserve duplicate detection. The proof and affine-map acceptance rules remain unchanged.
- Balanced scheduling uses the input-inclusive absolute deadline, a positive warmup of min(remaining/8, 2s), then three quarters of the remaining time for negative discovery, then positive fallback. Every branch still returns only a checked negative certificate or checked original-query witness. Legacy branch order and quarter-time negative reservation remain unchanged. Final fallback clears the negative proof. No stale proof/verdict combination was found.

## Resource boundary

The warmup reduces exposure to negative-game growth on easily witnessed unsafe inputs; it does not make the portfolio memory-safe. If warmup misses, the longer negative slice can still hit the external memory limit before fallback. Current negative discovery has deadline/work checks, **no explicit game-memory or graph-size cap**. Rc sharing does not bound distinct markings, game nodes, OR-target vectors, transfer caches, or the dense extracted proof. Positive search also retains its existing state cap rather than a byte cap.

A graceful internal limit is needed if the intended guarantee is that negative expansion cannot consume the memory reserved for later portfolio stages. Add a separately configured, conservative retained-memory/graph limit checked before growth; include distinct control cells, game nodes, edges/OR targets, transfer payloads, and extraction/checking headroom. Return Unknown/resource-limit and release stage data before fallback. A node count alone misses variable-width controls and large transfer lists. Until such a limit exists, describe balanced scheduling as an opt-in heuristic and retain the external memory supervisor.

The numeric work allowance is reused per stage; it is not a conserved whole-portfolio instruction or work budget. That behavior predates the new schedule, but the new warmup adds another stage. Keep whole-query wall/memory comparisons distinct from this work parameter.

The phase deadline is cooperative: preparation, allocation, destruction, and output can overrun a slice. Deriving each deadline from one `now` and clamping to the property deadline would remove tiny clock drift, but does not replace the external end-to-end deadline. No new serious deadline violation was found.

## Required validation before claims

Run the extended CLI tests after the cohort run is terminal, covering positive warmup acceptance, checked negative output, unknown/resource stops, and independent checker acceptance. Existing tests exercise verdict paths but do not isolate a missed warmup followed by graceful memory-limit fallback; that requires the internal limit first. A representative unsafe case whose witness exceeds the warmup is needed in the matched evaluation. No performance or coverage claim for balanced scheduling is established by this review.

## Inspected identities

- `src/main.rs`: `4873cbaeca08dd5c9d021ed2790f268445a8a69bc878418b54e4682f586e59f9`
- `src/raw_negative.rs`: `b1206c0c434c82507a03b6c57189c8665fcc4ee4dc325f25890ae21a90ec6026`
- `scripts/raw_invariant_check.py`: `b4cec15ad4f72626082e4dea8423246a349efd0d5412c5a385eeb0a61136c1e5`
- `src/raw_potential.rs`: `3829bc4db5274f3b334129083e3cc6e9749e284ae54742dd5d19249d17cbea3f`
- `tests/raw_negative_cli.rs`: `f141747d385693ccfee1bceddc662eb056297b71dfff55b929cffd45893f845c`
