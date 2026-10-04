# Raw potential allocation diagnosis

The frozen raw stress pilot reports `replicas_n8_racy` solved by BFS with a verified witness, while raw-potential crosses the sampled 2 GiB limit after about 0.294 s (observed 2,436,300,800 bytes). These are one-pass development observations, not repeated speed claims.

The actual raw query has 1,314 places and 512 response coordinates. `raw_potential::goals` builds dense place-length coefficient vectors for potentially every response pair, then `solve` truncates the completed list to 32. The upper coefficient-storage size is512² × 1,314 × 8 = 2,755,657,728 bytes before vector overhead. Therefore the existing comment that goal allocation is bounded independently of response-pair count is false. Source inspection supports this allocation mechanism; no allocation profiler has yet attributed the observed peak.

A focused fix is to retain at most 32 sparse candidate descriptors while ranking by the existing stable `(bound, nonzero count)` order, then materialize only those 32 dense vectors. Keep both unary and binary response forms and the existing deadline checks. This bounds candidate storage without weakening witness acceptance. A differential test against the old exhaustive ranking on small inputs should establish equivalent candidate choice when neither deadline expires; large-response stress can test the cap without allocating the old quadratic dense list. The frozen benchmark must finish unchanged before testing or timing a revised candidate.

## Implemented and measured repair

The sparse top-32 repair is frozen in `results/solver-original-sparse-v1`. Four Rust tests include 96 exhaustive small ranking comparisons, 28 deterministic deadline cuts, and the 512-response storage fixture. Clippy and the release build passed.

The full raw-potential rerun completed twice on all 18 selected sources (12 valid exports). It solved five valid cases in both repetitions, versus four in the original one-pass pilot, with no lost positive. All four previously memory-limited valid cases stayed below the sampled limit in both new repetitions. The eight-cell racy replica case now has checked witnesses in 1.44–1.49 seconds with 69,894,144–73,793,536 bytes peak sampled process-tree RSS. The old invocation exceeded 2 GiB and produced no accepted answer.

These are development results with different repeat counts, not a general speed comparison. Detailed records: `results/raw-stress-sparse-v1`; exact comparison: `research/raw-sparse-comparison.json`. The new frozen binary also contains the native PNML frontend, which is not used by these raw-query invocations.
