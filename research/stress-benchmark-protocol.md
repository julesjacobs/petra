# Stress benchmark expansion

The current development comparison is saturated: the frozen local-v1 portfolio solves all 256 properties twice at 5 seconds. This motivates a separate stress-development expansion. It does not replace the completed frozen evaluation comparison or turn correlated larger instances into independent evaluation data.

## Frozen inputs

- `benchmarks/stress-selection.json`: 23 models and 368 planned original ReachabilityCardinality property slots from the existing eight development families. For each family choose its last three published instances strictly after the largest previously selected ordinal, or all qualifying instances if fewer. Retain all properties, including trivial queries and import failures. No solver outcome was used in this selection.
- `benchmarks/stress-programs/manifest.json`: 18 raw SER source programs, comprising 14 new parameter cases and 4 explicitly marked bridge duplicates. Counters reach domain 127/stages 64, replicated registers 12 cells, and monitors require up to 2,560 advance requests. All are correlated extensions of existing families. Source-level serializability expectations are not solver answers.

Collection is performed separately from reachability timing. Retain source/archive hashes, import/export status and resource limits for every selected model/program. Do not silently replace a model whose import is expensive, or discard its property slots from the selected-set denominator. Distinguish failure to obtain a valid query from a solver returning unknown on a valid query.

## Measurement plan

1. Finish current local and remote measurements before starting heavy work on the corresponding host. Validate the new collection scripts with synthetic malformed archives and failure cases before collection.
2. Collect/import the entire MCC selection with a 120-second per-model wall allowance, 2 GiB memory safeguard, 512 MiB compressed archive and 2 GiB expanded archive limits. Raw SER export uses an explicit 60-second probe followed by a separately recorded full collection when feasible. Preserve partial artifacts. Sampled local memory limits are not kernel-enforced bounds.
3. Validate imported MCC predicates independently against their original XML; validation may compare semantics without running any solver. Validate raw JSON in a bounded worker before describing an export as a solver-ready query.
4. Pilot all successfully imported queries at 5 seconds using unchanged frozen candidate, frozen predecessor and unrestricted VerifyPN under the same original-input deadline. Keep unavailable property slots visible. On Linux retain single-core affinity and instructions/CPU/memory metrics, plus SMPT portable. A longer 30-second pass is a separate experiment, not a best-of-runs replacement.
5. Report attempted models/properties, valid imports, definitive answers, unknowns, failures and family-level results. Preserve every original property. An optional difficulty view derived from the complete pilot is explicitly development-only and must retain the full underlying report.

Increasing model size is a hypothesis about difficulty. Original-input conversion may dominate on large files; report that separately from successful conversion followed by difficult reachability search. Do not claim this corpus is harder until the pilot provides evidence, or claim a general performance win from a selected unresolved subset.

The independent evaluation plan remains `research/local-v1-evaluation-plan.json`; its candidate hashes and selected families are unchanged. New algorithms informed by those outcomes require newly reserved evaluation families for an independent generalization claim.

## Current collection and measurement status

All 23 MCC models and 368 properties were imported successfully. The single-core Linux pilot completed all 1,104 rows: frozen-v2 solves 119, portfolio-local solves 275, and unrestricted VerifyPN solves 341, with no definitive disagreement. The native methods in this pilot use the Python original-input frontend. These are one-repetition development results under a 5-second deadline and enforced 2 GiB memory limit. See `research/linux-stress-v1-analysis.json` and `results/linux-stress-v1-pilot/REPORT.md`. SMPT is not included in this pilot; the broader comparison remains outstanding. The harder set exposes a substantial remaining gap to VerifyPN.

All 18 raw sources were attempted. Twelve exports passed bounded structural validation; six hit the 120-second export deadline and remain separately unavailable. The bounded raw harness preserves all 18 sources in the denominator. The four-method pilot independently verified positives for five distinct queries; seven valid queries remained unresolved by every method. A subsequent two-repetition run of the sparse-candidate raw-potential variant solves the same five in both repetitions, while the other seven remain unresolved. See `research/raw-stress-unresolved-v1.json` for an outcome-selected development view, input hashes, and per-method statuses. The complete collection remains the benchmark denominator.

The older 256-property development set remains saturated by the candidate through both Python and Rust frontends in the completed paired comparison. These results motivate the expanded set but do not establish independence: the stress models and programs are correlated extensions of existing development families. New held-out families are still needed for a publication-level generalization claim.

## Latest raw solver progress

Exact compact state storage raises stable raw coverage from five to eight valid queries in the original-checker ablation. Removing implied potential goals then solves the largest monitor. Matched reruns with the same sparse independent Z3 checker verify eight queries for the compact predecessor and nine for the dominance-pruned variant, each in both repetitions, with no lost positives. The three locked queries remain unknown; six exports remain unavailable. The 10-second input-inclusive deadline still includes independent checking. See `research/raw-sparse-checker-matched-comparison.json`; retain earlier variants and their failures as separate experiments.
