# Accelerated-BMC development comparison

All960rows pass the saved-artifact audit: all192MCCdevelopment properties across
three Rust/Z3 BMC configurations and two frozen native controls. Every definitive
answer has a separately bounded independent check. No disagreements or validation
failures occurred. This is one shared-macOS run at a one-second whole-property
budget on canonical JSON branches; parsing original PNML/XML is outside this scope.

| Configuration | Reachable | Unreachable | Unknown |
|---|---:|---:|---:|
| Ordinary BMC |67|0|125|
| Singleton acceleration |68|0|124|
| Discovered-word acceleration |69|0|123|
| Frozen walk portfolio |101|85|6|
| Earlier frozen portfolio |98|85|9|

All configurations solve the47properties whose targets include the initial marking.
Their noninitial positive counts are20,21,22,54and51respectively. BMC variants are
witness-only methods; their zero negative counts reflect their interface, not
claims that those targets are reachable.

Discovered words gain3properties and lose2against singleton acceleration; they gain
3and lose1against ordinary BMC. Every one of their69positive answers is already
found by both frozen native controls. Even the diagnostic union of all three BMC
variants has only71positive answers and adds none over the frozen walk portfolio.
This union is not an implemented solver result. See audit.json for complete lists.

## Diagnosis and next action

Each BMC variant hits the dense-summary cell limit on80branch attempts spread
across48properties. Among those48, the native walk portfolio finds21positive
answers. The encoder emits sparse formulas but still constructs dense
word-by-place summaries and the driver correctly caps that representation.
This prevents assessing the algorithm on many larger nets. Implement genuinely
sparse summaries with explicit work/output limits before investing in additional
vocabulary heuristics. Do not merely remove the resource limit.

The current implementation also rebuilds Z3 at each depth. Published ABMC uses
incremental prefix models and dynamic acceleration; see the separately sourced
assessment in research/accelerated-bmc-related-work-v1. Static cycle discovery
plus fresh-SMT depth queries is not a reproduction of that algorithm.

## Reproducibility and limits

Plan25d4ee18b974f1f2180dfdd98486fe3b0448d94e3a8fbe7e893acdc28264d6ee
freezes input identities, Rust/Z3/python interfaces, all source, binaries, limits,
seeded query order and rotated method order. Artifacts are under
results/abmc-mcc-development-v1 and results/solver-abmc-mcc-development-v1.
The frozen macOS walk-sparse-v1 binary matches its original provenance; every
one of its200source files is unchanged in the walk-sparse-v2 Linux packaging.
Those platform-specific executables remain distinct. No rebuild was needed.

Ten synthetic capability cases passed before launch, including positive and
negative answers for both controls. An initial launch from the nested source
snapshot used the wrong workspace root and failed before creating an execution
receipt or any rows. The failed log is preserved. The corrected launch executed
the hash-verified identical controller from the workspace root; session34323
terminated0. The complete matrix and original frozen plan are unchanged.

Memory is sampled across process trees at2GiB, not cgroup-enforced on macOS.
Validation uses separate30-second/2GiB limits. No build or other solver benchmark
ran locally during collection, but ordinary agent activity included paper metadata
retrieval, text extraction and two-page PDF rendering. This shared-host screen
cannot establish stable timing. Retain all failures and near-deadline outcomes;
repeat final comparisons on controlled Linux before a speed claim.

No new competitive advantage, novelty, or publication-readiness conclusion follows.
The existing walk portfolio remains the stronger implementation on this cohort.
