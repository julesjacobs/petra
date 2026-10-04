# Harder benchmark set: current evidence and priorities

The development set already contains difficult application queries. The next
priority is the measured application gap, alongside the separate synthetic
diagnostics. Increasing the sizes of easy synthetic encodings alone would not
establish a stronger solver for applications.

| Track | Complete selection | Evidence |
|---|---:|---|
| MCC application stress | 368 queries | Previous full Linux comparison: Rust 298, VerifyPN 345; 70 Rust-unresolved, 58 VerifyPN-only, 12 unresolved by both Rust frontends and VerifyPN |
| Boolean consistency | 34 queries | Latest complete Linux comparison: new Rust 24, predecessor 8, SMPT 10, VerifyPN 5; 10 unresolved by every configuration |
| Raw SER stress | 18 sources | 12 valid queries, all solved twice by the raw portfolio; 6 export timeouts |
| Diverse SER | 12 sources | 10 component-limit failures and 2 memory-limit failures; no solver-ready queries |
| Reserved evaluation | 16 models / 256 property slots | Eight families reserved, uncollected, excluded from tuning |

These counts have different denominators and must not be pooled. The latest
symbolic candidate has not been compared across the full application set.
Source expectations and source-formula oracle answers are distinct from
independently checked reachability answers.

## Development priorities

1. Use the 58 VerifyPN-only application properties to diagnose mechanisms
   our solver is missing. The filters are in `benchmarks/stress-challenges-v1`.
   Re-run the full 368 queries after improvements to detect regressions.
2. Use the 12 jointly unresolved application properties for harder search and
   proof experiments. These are selected from observed outcomes and therefore
   remain development data, not independent evaluation.
3. Retain all 34 Boolean-consistency queries. Corpus v3 fixes PNML/XML metadata
   compatibility with SMPT without changing any canonical net or target.
   Source SAT formulas are easy for a dedicated solver; this track diagnoses
   reasoning through a Petri-net encoding.
4. Make diverse serializability queries exportable before expanding their
   parameter ladder. Eager semilinear construction currently prevents any
   reachability measurement for the new program families. Export failure is
   recorded separately from a solver timeout.
5. Freeze the candidate and competitor configurations before collecting and
   measuring the reserved evaluation families. Do not use these families to
   choose solver heuristics.

Single-core Linux comparisons use CPU 8, enforced 2 GiB, user-space instruction
counts, and original-input deadlines. Independent native checking is bounded
separately. Preserve failed runs and full selections. Longer deadlines are
separate experiments, never replacements for unfavourable short runs.

The updated catalog is `benchmarks/development-catalog-v3.json`. Previous
catalogs and results remain unchanged. The five-method synthetic rerun uses
`research/linux-dag-sat-v2-plan.json`; all 170 rows completed successfully. Audited results are in
`research/linux-dag-sat-v2-analysis.json`; current difficulty filters are in
`benchmarks/boolean-consistency-challenges-v2`. All 24 new Rust answers passed
independent checking. There were no definitive disagreements or tool errors.
The new solver gained 16 answers over the predecessor and lost none. This is
a one-repetition synthetic development result, not a general superiority claim.
