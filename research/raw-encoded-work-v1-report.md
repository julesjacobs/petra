# Encoded-key accounting restores the raw regression proof

The repaired compressed candidate checks all27available slots in the original
raw cohorts again:14reachable and13unreachable. The preceding compressed version
checked25/27; the dense baseline checked27/27. These28source slots represent24
unique programs, including four bridge duplicates and one unavailable export.
Every definitive answer has a saved independent original-query check.

The two lost slots were the same `write_skew_n5_pairlocked` program in both
cohorts. The completed phase diagnostic established an early logical-work stop
inside negative discovery; subsequent positive fallback consumed the remaining
solver time. See `raw-n5-control-diagnostic-v1-report.md`.

Only interner accounting changes in this candidate. Conversion charges two
dense passes. Lookup charges twice the encoded payload words plus metadata;
insertion charges that allowance again only on a miss. Sparse coordinates and
values both count as words. Failed charges cannot insert a new key. These are
declared logical allowances, not CPU instruction counts or worst-case hash-table
runtime bounds. External wall and memory limits still apply. Storage, discovery
semantics, certificate format and independent checker remain unchanged.

Both n5 proofs are independently accepted, in35.01s and46.67s whole-query wall,
with sampled process-tree peaks around1778/1780MiB. These measurements include
the independent checker; they do not isolate solver storage. One repeat on a
shared Mac does not establish a speedup. Numeric work limits stayed fixed while
their accounting changed, so this is not an equal-work comparison.

Validation:233Rust tests passed, one diagnostic test remained intentionally
ignored; formatting and Clippy passed after correcting the initial formatting
check. Original logs are retained. The complete frozen source derives from the
repaired312-file package, with only `src/raw_negative.rs` changed and the new
freezer added. Binary SHA256:
`212eaec32aa0b6e845e86a4ce1349bbb721faecad7d9fe304266ad38b32a0823`.

The28-row qualification completed with exit0, passed saved-artifact/classifier
reconciliation, and rechecked61artifact hashes. Evidence:
`raw-encoded-work-cohorts-v1-plan.json`,
`raw-encoded-work-cohorts-v1-verification.json`,
`raw-encoded-work-cohorts-v1-execution.json`, and
`results/solver-raw-encoded-work-v1/provenance.json`.

The separate harder transfer experiment also completed and passed artifact audit:
all12source slots retained, six independently checked positives, three strict
solver timeouts and three unavailable exports. There is no coverage gain on
these cases. See `transfer-raw-encoded-work-v1-verification.json` and its frozen
plan; session80089exited0. The regression repair therefore supplies no proof for
the strict cases and no general competitive claim.
The ongoing Linux ordinary-net comparison uses its original frozen candidate;
this local raw-path repair does not alter that run.
