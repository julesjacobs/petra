# Sparse duplicate-node keys: checked n5 proof

The independent checker validates every dense control vector before encoding its
nonzero position/value pairs for duplicate-node detection. Fixed dimension and
exact validated u64 values make this encoding injective. Component identity
remains part of the key. All26 checker tests pass, including a new fixture covering
zero padding, different occupied positions, distinct components, maximum u64
values and duplicate rejection. Original transition, affine-map and schema
acceptance rules are unchanged.

A matched proof-only experiment checks the same saved125MiB answer with both
checker versions, with120s/2GiB/10Bwork. Dense keys exceed2GiB after10.3s; sparse
keys accept the proof in24.9s overall, peaking around1.73GiB. The parent records
all limits and statuses; proof-only time excludes generation and cannot stand in
for an end-to-end solve.

The subsequent eight-row end-to-end comparison uses the same frozen streaming
binary, four original inputs,60s/2GiB/10Bwork and separate frozen runner closures.
Dense keys solve3/4; sparse keys solve4/4. n5 is independently checked in40.4s,
peaking at1776MiB. All seven definitive answers have successful independent
checks, and artifact reconciliation passes without disagreements. This is a
local diagnostic coverage gain, not a competition or novelty claim. Earlier
30-second and memory-limited outcomes remain preserved.

All28source slots across both complete cohorts are now registered for60-second
requalification with direct raw-negative and raw-portfolio, one repeat each.
The24unique programs, four bridge duplicates and one export failure are retained.
The old portfolio still reserves only a quarter of solver time for negative
search. Larger work allowances have already exposed memory-limit failures on
known unsafe cases before positive search. This is a scheduling regression to
fix, not evidence that those programs became intrinsically hard.

Artifacts: `raw-checker-sparse-identity-v1-{plan,results}.json`,
`raw-checker-end-to-end-v1-{plan,analysis,verification}.json`, and
`raw-hardness-requalification-v2-plan.json`. The latter has an explicit
registration erratum correcting inherited descriptive text and derived totals;
its registered commands,56rows,60s limits and source selection are unchanged.
