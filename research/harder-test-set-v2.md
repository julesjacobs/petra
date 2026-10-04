# Harder development test set

The new 34-query Boolean-consistency suite has **25 queries unresolved by both
the frozen Rust portfolio and VerifyPN** in a complete five-second Linux
pilot. This adds measured search difficulty to the existing 368-property
application stress corpus. Keep the two suites in separate result tables.

| New suite, all 34 original queries | Reachable | Unreachable | Unresolved |
|---|---:|---:|---:|
| Frozen Rust portfolio-local | 8 | 0 | 26 |
| VerifyPN, unrestricted default | 4 | 1 | 29 |

All 68 invocations completed: one repetition, CPU 8, enforced 2 GiB limit,
original PNML/XML parsing inside the five-second deadline, user-space
instruction counters available for every run. There were no memory-limit
failures or definitive disagreements. All eight Rust witnesses passed the
independent Python checker, separately bounded outside solver timing.
VerifyPN certificates were not independently checked. These are exploratory
development results on a shared Linux host, not a general superiority claim.

The suite contains random 3-CNF encodings across four sizes and three clause
ratios, plus positive/negative pigeonhole pairs. Selection was fixed before
solver results. Every net is an ordinary 1-safe net. Full inputs, formulas,
parameters and hashes are in
[`boolean-consistency-v1`](../benchmarks/boolean-consistency-v1/manifest.json).
The encoding argument, exhaustive small-instance checks, and source-oracle
caveat are in [`boolean-consistency-v1.md`](boolean-consistency-v1.md).
In particular, the source Boolean formulas are easy for Z3: the measured
challenge is reasoning through their Petri-net encoding. Keep this diagnostic
separate from real application workloads.

The complete results are in
[`REPORT.md`](../results/linux-boolean-consistency-v1/REPORT.md) and
[`runs.jsonl`](../results/linux-boolean-consistency-v1/runs.jsonl).
[`boolean-consistency-v1-analysis.json`](boolean-consistency-v1-analysis.json)
checks matrix completeness, disagreements and agreement with source
expectations/oracle answers. The 25 jointly unresolved cases have a filter
in [`boolean-consistency-challenges-v1`](../benchmarks/boolean-consistency-challenges-v1/README.md).
These are outcome-selected development views; retain all 34 for comparisons.

The existing application set remains useful: Rust left 70/368 unresolved;
12/368 were unresolved by both candidate frontends and VerifyPN. Its full
results and development views remain unchanged. The newly reserved MCC
families remain uncollected and excluded from tuning.

Twelve new serializability sources cover ring write skew and optimistic ABA
validation. **None exported successfully**: ten semilinear component-limit
panics and two memory-limit failures. They are prospective benchmarks, not
twelve additional hard solver queries. Every failed attempt is preserved;
see [`diverse-ser-v1-collection-results.md`](diverse-ser-v1-collection-results.md).
The next obstacle there is eager construction of the serial target's
semilinear representation, despite exporting the unreduced Petri net.

[`development-catalog-v2.json`](../benchmarks/development-catalog-v2.json)
indexes the separate tracks. The next solver experiment should use the full
new suite and the application stress set; tuning filters help diagnosis but
must not replace their full denominators.
