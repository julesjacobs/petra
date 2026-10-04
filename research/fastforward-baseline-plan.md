# FastForward baseline preparation

2026-09-27. Source/metadata inspection only. No installation, build, solver execution, benchmark-suite download, or evaluation-set inspection. The compatibility conclusions below come from the pinned source, not README claims alone.

## Pins and provenance

- Repository: [p-offtermatt/FastForward](https://github.com/p-offtermatt/FastForward).
- Inspected commit: **`bf6bb6fefd03c640af25b2f5ea0a0dc053d47736`** (current `master` at inspection). [Pinned tree](https://github.com/p-offtermatt/FastForward/tree/bf6bb6fefd03c640af25b2f5ea0a0dc053d47736).
- Root `LICENSE.txt`: MIT, copyright 2020 Michael Blondin, Christoph Haase, Philip Offtermatt.
- Paper: [Directed Reachability for Infinite-State Systems, TACAS 2021](https://doi.org/10.1007/978-3-030-72013-1_1).
- Published artifact: [10.6084/m9.figshare.13573592.v1](https://doi.org/10.6084/m9.figshare.13573592.v1), published 2021-01-14. [Versioned API metadata](https://api.figshare.com/v2/articles/13573592/versions/1) reports MIT and `FastForward.zip`, **960,594,789 bytes**, computed MD5 **`78521fa06a5b88257b42d4bb519dce35`**, [file 26048870](https://ndownloader.figshare.com/files/26048870). Not downloaded. Compute and freeze SHA-256 after a later download; MD5 here is upstream identity metadata, not a modern integrity guarantee.
- The inspected repository revision has not been established as the artifact’s source revision. Label these configurations separately until compared.

## Actual target and net interface

Inspected `ParserPicker.cs`, `CommandLineOptions/CommandLineOptions.cs`, `PetriNet/Parsers/LolaParser/LolaParser.cs`, `PetriNet/Parsers/MCCParser/{PNMLParser,MCCFormulaParser}.cs`, `PetriNet/MarkingWithConstraints.cs`, and `PetriNet/Transitions/UpdateTransition.cs` at the pin.

The reliable candidate input is a generated `.lola` weighted P/T net plus `.formula` containing a disjunction of conjunctions of **per-place `p = k` or `p >= k`**, with nonnegative integer constants. Unmentioned places have no restriction beyond nonnegativity. Arc weights, initial tokens, target constants, and markings are C# `Int32`; our `u64` domain is broader. `UpdateTransition` checks the original precondition and then consumes/produces, so read arcs are represented, but arithmetic is not explicitly checked for overflow in the inspected implementation.

| Our canonical target | Direct supported encoding |
|---|---|
| Exact marking | Equality for every place, including explicit zeros. |
| Coverability target | Lower bounds on requested places. |
| Mixture of per-place equalities/lower bounds | Native `MarkingWithConstraints`. Merge repeated constraints on a place first; the parser builds dictionaries and cannot take duplicate keys. |
| Singleton `a*p >= b`, `a>0` | Exact normalization to `p >= max(0,ceil(b/a))`, subject to integer range. |
| Singleton `a*p = b`, `a!=0` | Exact normalization to `p=b/a` if integral and nonnegative; otherwise branch is unsatisfiable. |
| Upper bound `p<=k`, nontrivial sum, or mixed-sign relation such as `p>=q` | **Not native.** Some finite cases can be compiled to a disjunction, but that is a separate transformation with its own proof and charged cost. General signed relations must not be silently weakened. |
| Constant true/false constraints | Adapter may simplify exactly. It must explicitly handle an all-true or all-false property; empty/malformed formula behavior must not decide this implicitly. |
| Disjunction of supported branches | Native target list; encode one parenthesized conjunction per branch. Preserve original EF/AG polarity in the outer result adapter. |

The `.formula` parser is regex-based and does not implement general LoLA syntax. Unsupported input can be misinterpreted rather than cleanly rejected. Generate only a restricted grammar with canonical `p0`, `t0` names, then independently round-trip its semantics. Do not pass arbitrary existing LoLA formulas without validation.

**Original MCC XML formulas are not a working CLI interface at this revision.** `ChooseFormulaParser(...xml)` throws `NotImplementedException`, and `MCCFormulaParser.ReadFormula` also throws. The presence of an unfinished MCC parser is not evidence of support.

PNML net parsing exists, but explicit inscription parsing uses `SelectSingleNode(...text).Value`; for an XML element, this is a potential parsing defect that requires a weighted-arc test before trusting direct PNML input. For initial integration, a checked `.lola` conversion is preferable. Do not label that conversion as direct original-input support.

Concrete development examples inspected:

- `Echo-PT-d02r15__RC00`: `p507>=1`; target is directly representable.
- `CANConstruction-PT-020__RC05`: counterexample target `p138>=1 AND p711-p111>=0 AND p963-p457>=0`; not directly representable.
- `JoinFreeModules-PT-0005__RC09`: includes `p9-p13>=0` and `p17-p12>=1`; not directly representable. Our necessary local target used for a negative certificate is **not an equivalent target to benchmark FastForward on**.

A complete support inventory should be produced later from the frozen development manifest using these syntactic rules, before running either solver on that subset. Do not silently drop unsupported branches of an original property. Keep unsupported-property counts in the report. No support census or solver run was performed here, and no evaluation inputs were opened.

## Build constraints discovered

`artifact/src/fastforward.csproj` targets **`netcoreapp3.1`**. Direct package versions are CommandLineParser 2.7.82, CsvHelper 12.3.2, FibonacciHeap 1.1.8, MathNet.Numerics 4.12.0, Microsoft.NET.Test.Sdk 16.4.0, Microsoft.Z3.x64 4.8.7, Newtonsoft.Json 12.0.3, OptimizedPriorityQueue 4.2.0, Simbool 0.1.0, Xunit 2.4.1. The Gurobi assembly reference is `gurobi90.netstandard20.dll`.

The README’s “without Gurobi” command cannot be accepted as a verified recipe:

- The project unconditionally appends `GUROBI` to `DefineConstants`.
- `HeuristicPicker.cs` has its own `#define GUROBI`.
- `SearchQueryEntrypoints.SaturationSearch` contains Gurobi calls outside a method-wide conditional compilation guard.
- `nuget.config` clears all package sources.
- Both republish scripts delete an existing benchmark-output directory and move the build there; use explicit build/output directories instead.

A no-Gurobi build therefore needs a documented compatibility patch or a different verified source snapshot. Merely passing `GUROBI=false` does not establish that those dependencies disappear. A .NET upgrade likewise changes runtime behavior and requires its own labeled build; it must not masquerade as a reproduction of the published configuration. The old runtime’s Linux dependency compatibility remains untested.

**No purported reproducible setup script was emitted:** a complete dependency/build recipe is not yet verified from the available source, and a script claiming otherwise would hide these concrete blockers. Next setup step after timing runs: inspect the published artifact’s installation instructions/source, select and pin one runtime/toolchain, restore packages with explicit sources and a lock file, and either reproduce the original Gurobi configuration or make and review a minimal labeled no-Gurobi compatibility patch. Record the source diff, SDK/runtime versions, package lock, native Z3/Gurobi versions and licenses, and binary hashes. Gurobi-dependent heuristics require a working licensed Gurobi installation; do not substitute a weaker available heuristic under the same label.

## Configurations and harness contract

Verified source-level CLI shapes (not yet executed):

```text
fastforward best-first model.lola query.formula -h syntactic
fastforward a-star model.lola query.formula -h qReachability
fastforward best-first model.lola query.formula -h qReachability
fastforward a-star model.lola query.formula -h QMarkingEQGurobi
fastforward best-first model.lola query.formula -h QMarkingEQGurobi
```

Use the structural GBFS mode and both algebraic search orders as separate configurations where available. `-p` requests forward pruning; its work belongs inside the deadline. `--precompute-max-tokens` is restricted to a special net class and must not be enabled generally. Backward-pruning flag execution and each heuristic’s full target domain still require source/tests before a fair configuration is frozen.

`SearchQueryEntrypoints` emits JSON diagnostics with `path` as comma-separated transition names or `"unreachable"`; an empty string can be a valid zero-step witness. Exit status alone is not a verdict. The harness must parse the specific successful JSON record, treat process timeout/OOM/failure as unknown/error, and replay every positive path on the original query with exact Python integers. Negative verdicts remain externally unchecked unless a separate certificate is supplied. The `Int32` arithmetic boundary must be addressed: either certify finite bounds fitting that range or document and audit an overflow-checking compatibility build. Valid initial weights alone do not prove all intermediate counts fit.

Two fair input tracks are available:

1. **Original-property frontend track:** inside one shared cgroup deadline, read original PNML/XML, select the exact property ID/polarity, translate and normalize, serialize `.lola`/`.formula`, start FastForward, and solve all its disjuncts. Charge Python/runtime startup, conversion, pruning, and .NET startup. Compare with our original-input frontend under the same scope. Check translation and returned witnesses outside timing.
2. **Common-representation backend track:** freeze semantically identical `.lola`/`.formula` and Rust JSON inputs with hashes and independent correspondence checks. Exclude translation for every tool, label this backend-only, and retain a separate end-to-end track.

Using preconverted FastForward input against timed Rust PNML translation, or vice versa, would not establish an end-to-end advantage.

## Published suites as additional benchmarks

The [paper’s experiment section](https://arxiv.org/html/2010.07912v1) reports **61 positive coverability**, **30 positive SyPet reachability**, and **127 positive random-walk reachability** instances. The latter were generated from 33 larger nets and filtered to remove cases where FastForward or LoLA found a witness of length at most 20. They are a useful established challenge suite, but are positive-heavy and selected using those tools; preserve that fact rather than describing them as unbiased held-out negatives.

Repository metadata shows `artifact/benchmark/nets/{coverability,coverability_prepruned,random_walk,random_walk_prepruned,sypet,sypet_prepruned}`. Their exact file counts, identities, and correspondence to the archived paper artifact remain unverified. The repository also contains unrelated workflow data; directory presence alone is not paper-suite membership.

After live runs finish, acquire the versioned artifact once, preserve the original archive/hash/license, and import the paper’s explicit suite lists. Prefer original unpruned nets for end-to-end comparisons; keep prepruned inputs as a separately labeled common-input ablation. Preserve all target zeros for exact reachability. TTS imports need special care: source code defaults to an upward-closed/parameterized initial state, while `--single` changes it to one token. Translate the original initial-set semantics explicitly rather than treating every TTS instance as a fixed initial marking. Freeze exact conversion maps and witness replay tests before any benchmark claim. Check cross-suite duplicates against our existing classical SMPT inputs by net/initial/target semantics, not just filenames.
