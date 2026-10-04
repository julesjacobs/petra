# Source-only Rust original-input review

Inspected `src/pnml.rs`, `src/original.rs`, the pending `src/main.rs` integration, existing PNML tests and Python verifier interface. No tests/builds/solver measurements were run.

## Concrete parser defect: XML text is truncated at comments

`src/pnml.rs` calls `Node::text()` for marking/arc numbers (line81), integer constants (line231), place references (line245), and property IDs (line368). The installed roxmltree implementation returns only the first text child of an element, or none if the first child is a comment. It does not concatenate XML character content separated by comments or processing instructions.

Example accepted well-formed simple-content XML:

```
<initialMarking><text>1<!-- comment -->2</text></initialMarking>
```

The XML character content is `12`; the parser reads `1`. A net containing this marking and no transitions, queried with EF(p>=10), consequently changes from reachable to unreachable. The same issue can silently change integer constants and weighted arcs. A leading comment can instead reject an otherwise valid number. Split property IDs/place references can select or resolve a truncated identifier.

Fix with one leaf-text helper that rejects element children and concatenates direct text-node contents, ignoring comments/processing instructions. Use it consistently for numeric leaves, place-reference leaves and IDs. Add fixtures with split/leading comments and processing instructions; check the numeric example against the independent Python importer. This is a semantic defect established from source inspection, not an executed regression result.

## Arithmetic and aggregation checks

No defect found in the reviewed DNF logic: negation switches conjunction/disjunction, AG negates the target once, and negated integer <= becomes left-right>=1. BigInt cancellation precedes checked i64 conversion. The1024branch cap fails explicitly. False predicates produce zero branches, which correctly aggregate to unreachable (AG true when the violation target is false).

The whole-property timer starts before PNML/XML file reads. Branch budgets divide actual remaining property time; returned answers at/after the deadline are downgraded to unknown, including final aggregation. An external deadline remains necessary during parsing, engines with advisory budgets and output serialization. Sequential unknown-then-witness aggregation is sound; every disjunct must be refuted for a negative answer.

Typed arcs, unknown semantic child elements, capacities, non-bipartite endpoints, duplicate IDs/markings and arithmetic overflows fail explicitly. NUPN and restricted Tina display metadata are deliberately ignored. Element recognition uses local names rather than validating namespace URIs; this is a broader input-contract consideration, not a demonstrated wrong answer on the intended MCC ordinary-P/T format.

## Required verifier integration boundary

The currently present bounded validator accepts the Python frontend's `translation.json` plus `attempts[{branch,exit_code,outer_timeout}]`. Rust instead emits `kind=original-property-v1`, `property_kind`, and `attempts[{branch,outcome}]` without translation artifacts. It needs a distinct checked dispatch before benchmarking; feeding it to the existing Python validator cannot work.

For Rust output, require exact property ID, kind, branch_count and a unique contiguous branch prefix. Validate each embedded branch outcome against the corresponding **canonical original net/target**, then independently recompute aggregation and property_truth. Require every canonical branch for negative acceptance, including exact zero-branch agreement. A top-level unknown caused by the whole-property deadline must not be upgraded from surviving branch proofs: the wrapper can detect deadline expiry after a branch returned. Likewise reject definitive output after an outer timeout. Original net/target proof checking must not trust the Rust-reported branch_count or property_truth alone.

The current source forbids `--pnml --verify`; that is a CLI limitation rather than silent acceptance. Keep external Python verification explicit until a native whole-property verifier exists. Pending integration may address these observations; re-read it before final review.
