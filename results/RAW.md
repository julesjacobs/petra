# Raw-query benchmarks and response-potential search

The frontend now exports the original request-tracking Petri net and the serial semilinear language before complement construction, target decomposition, net pruning, or solver invocation. Optional semilinear simplifications are disabled. One exported file represents a whole program's counterexample query. It is not comparable to one of the previous 218 simplified disjuncts.

The new native `raw-potential` engine finds more counterexamples by deriving linear bounds valid for every serial response vector and searching for violations. It uses reduced/directed search with lifted original-net traces, then direct search if necessary. Exact semilinear membership checking never interprets a resource limit as nonmembership. No raw engine currently proves unreachability.

## Generated programs

All runs use a two-second solver budget and 200,000 states, with a four-second outer process limit. Processes run sequentially. All positives pass independent Python replay and Z3 checks against every excluded linear set, outside the timed run. Wall times are exploratory on a shared host.

| Corpus | Method | Counterexamples found | Unknown | Repetitions |
|---|---|---:|---:|---:|
| 24 generated programs | raw-bfs | 10 | 14 | 3 |
| 24 generated programs | raw-potential | 16 | 8 | 3 |
| 24 generated programs, initial baseline | raw-z3 | 3 | 21 | 1 |
| 5 larger exported programs | raw-bfs | 0 | 5 | 1 |
| 5 larger exported programs | raw-potential | 2 | 3 | 1 |
| 5 larger exported programs | raw-z3 | 0 | 5 | 1 |

There were no errors or unstable verdicts in these runs. All 16 source programs expected to be nonserializable have checked counterexamples in every repeated `raw-potential` run. The eight expected serializable programs remain unknown; their source-level correctness arguments are not solver proofs.

`raw-z3` is a new direct quantified bounded-model-checking baseline, not the artifact's SMPT configuration. All five larger Z3 runs reached the outer timeout. The initial baseline was collected separately; the repeated native comparison uses the frozen final native binary on identical query bytes.

The larger programs were generated after freezing the search design, without retuning to their results. They extrapolate the same families and are not an independent benchmark distribution. Six sources were attempted: five exported, while the locked domain-31 counter exceeded the ten-second frontend limit. The new engine finds witnesses for the 128-advance monitor and eight-cell replicated register in about 0.53 and 0.44 seconds respectively.

Remaining larger cases at two seconds:

- `counter_d31_s16_racy`: expected nonserializable, 590-place net.
- `monitor_d5_c64`: expected nonserializable, requires 320 advances.
- `replicas_n8_locked`: expected serializable, 1,570-place net; requires a negative proof.

These retain challenges in search depth, interleavings, and negative proofs after the improvement. Frontend scalability is a separate challenge: serial-language construction still has an existing component guard and can grow exponentially.

## Original artifact programs

Of 47 original sources attempted with a five-second frontend limit, 39 exported, five hit the existing component guard, and three timed out. On the 39 exported whole-program queries, one two-second run found 14 counterexamples with raw BFS and 17 with `raw-potential`, leaving 25 and 22 unknown respectively. There were no errors, and every positive passed independent checking. The missing eight exports are not counted as solved queries.

The largest exported target has 147,464 components and remains unknown for both engines. Its approximately 295 MB JSON takes substantial time to parse; measured process wall times include parsing in addition to the solver budget. This exposes frontend and representation costs hidden by the old simplified-disjunct corpus.

## Evidence and reproduction

- [Repeated native comparison](raw-comparison/REPORT.md) and its `runs.jsonl`/`environment.json` record all repetitions and source/binary hashes.
- [Initial direct baselines](raw-initial/REPORT.md).
- [Larger-program comparison](raw-scaling/REPORT.md).
- [Original-source comparison](raw-original/REPORT.md).
- [Export boundary, input format, corpus provenance, and commands](../research/raw-benchmarks.md).
- [Generated families and semantic expectations](../research/harder-programs.md).

The implementation passed 97 Rust tests and Clippy with warnings denied; one pre-existing artifact-dependent test is ignored. Tests include exact membership differential checks and a regression ensuring response places survive raw-search reductions.
