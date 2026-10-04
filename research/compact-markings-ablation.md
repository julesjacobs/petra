# Compact exact markings

Guided search and direct raw search now store each concrete marking as either a dense array of token counts or a sorted list of nonzero `(position, count)` pairs, choosing the smaller payload. Representation choice is deterministic for a fixed dimension. Expansion restores the exact marking into one reusable dense buffer; original witness replay remains unchanged.

Quotient keys use the same adaptive encoding for exact active coordinates and retain every signed passive observation in an `i128` array. No observation or token count is dropped. The quotient equivalence relation, candidate order, and search queues are unchanged; resource limits may still change which attempts complete. Dense active coordinates now use `u64` rather than widening every token count to `i128`.

Verification: 217 Rust tests and all-target clippy passed. Tests exhaust all 1,093 markings of lengths zero through six over `{0,1,u64::MAX}`, checking exact reconstruction and distinct hash keys within each dimension. Projection positions and a 10,000-place sparse marking are checked separately. A further 8,192 sampled keys compare against the former dense key, including signed arithmetic overflow and visited-set equivalence. Existing guided tests compare bounded nets against independent BFS and replay quotient/capped witnesses.

Frozen source/binary: `results/solver-compact-markings-v1`. Experiment: `research/raw-compact-plan.json`, all 18 raw sources, two repetitions, 10-second input-inclusive deadline, 2GiB sampled RSS. Compare with the indexed-successor predecessor. Results remain pending until all 36 rows complete.

## Completed result

All 36 rows completed. Stable verified coverage rises from 5/12 to 8/12 valid queries with no lost positives; six export failures remain separately unavailable. New positives in both repetitions are monitor_d4_c256 (2.170/2.276s), monitor_d5_c256 (2.411/2.422s), and replicas_n10_racy (9.765/9.826s). Each result includes independent original trace replay and Z3 nonmembership checks inside the 10-second envelope. The replica result is close to the deadline and needs further repeated measurement for robustness.

The remaining largest monitor, monitor_d5_c512, changes from two memory-limit failures to two timeouts, with sampled process-tree peak memory about 144–151MiB instead of exceeding 2GiB. Three locked variants also remain unknown. Their source-level expectations are not negative proofs.

Exact before/after statuses, times, and peak RSS are in `research/raw-compact-comparison.json`. These are development measurements on a shared Mac, not a general competition result. A separate diagnostic run will examine the remaining monitor's per-goal scheduling; it must not replace this complete fixed-envelope report.
