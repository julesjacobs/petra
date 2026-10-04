# Balanced portfolio pilot: four checked answers

All eight registered rows completed and artifact verification passed. The opt-in
`raw-portfolio-balanced` solves 4/4 selected queries; legacy `raw-portfolio` solves
1/4. All five definitive answers have saved successful independent checks. No
verdict disagreement occurred.

| Query | Legacy portfolio | Balanced portfolio |
|---|---|---|
| write_skew_n3_racy | Memory limit | Checked reachable, 0.782s |
| write_skew_n3_pairlocked | Checked unreachable, 0.194s | Checked unreachable, 2.213s |
| write_skew_n5_racy | Memory limit | Checked reachable, 0.713s |
| write_skew_n5_pairlocked | Solver timeout | Checked unreachable, 41.551s |

This matched local diagnostic uses the same frozen binary, inputs and independent
checker, one repetition, a 60-second input/check-inclusive deadline and sampled
2 GiB process-tree RSS. The solver receives 80% of remaining time. The configured
100 million state limit supplies 10 billion negative/checker work per applicable
stage; it is not a conserved aggregate portfolio work budget. Phase diagnostics
were enabled for both methods.

Balanced scheduling first gives positive search min(remaining/8, 2s), then gives
negative discovery three quarters of remaining time, followed by positive
fallback. The existing portfolio keeps its quarter-time negative-first schedule.
The racy witnesses finish during warmup; pairlocked n5 receives enough negative
time for its checked proof. Balanced scheduling adds overhead on the small
pairlocked n3 case. Its sampled n5 proof peak is 1778.7 MiB.

These outcomes identify work, representation/resource and scheduling limitations
behind the larger raw misses, not established intrinsic search hardness. The
pilot is selected development evidence, not a competitor comparison or stable
speed claim. A missed warmup can still expose negative discovery to memory
exhaustion: no internal graph-memory limit is implemented. Full balanced cohort
qualification remains separate and must preserve all28 source slots,24 unique
programs, four bridges and the pairlocked n6 export failure.

Evidence: `raw-balanced-pilot-v1-plan.json`,
`raw-balanced-pilot-v1-analysis.json`, `raw-balanced-pilot-v1-verification.json`,
and `raw-balanced-review-v1.md`. The audit reconciles saved checker results and
frozen identities; this report did not rerun proofs or establish source-to-query
translation correctness. Binary SHA-256:
`a642f91c60868b1530053a47b0c847a6eeaa8c754ca0389062e2eb5f9232c664`.
