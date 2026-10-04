# Rust original-input frontend integration

2026-09-27. Source-only design; no changes to `main.rs`/`lib.rs`, no builds or tests during collection. The parser module’s completed validation was 9 tests, including exact agreement on all 256 development properties / 377 canonical branches. No evaluation failures were consulted in this design.

## Interface

Add an explicit input mode:

```text
vass-reach --pnml model.pnml --xml properties.xml --property-id ID \
  --method portfolio-local --seconds 5 --max-states 200000
```

`--pnml` conflicts with `--net`, `--json`, and `--raw`; it requires `--xml` and `--property-id`. `--property-id` is legal only with `--pnml`. Keep existing Tina `--net --xml` semantics and the default solver unchanged. Reject `--unlimited` in original-property mode: this mode has one finite whole-property deadline. Initially reject the existing single-problem `--verify` and `--export-json` flags with this mode rather than assigning them ambiguous multiple-branch meanings.

Use the existing `pnml::parse` result directly:

```rust
ParsedQuery {
    net: Problem,              // Empty target, original IDs/order.
    property_id: String,
    kind: PropertyKind,         // EF or AG.
    targets: Vec<Vec<Constraint>>,
}
```

Factor the current method match into `solve_problem(&Problem, &SolverOptions, Duration) -> Outcome`. Keep file paths and original-property aggregation outside that function. This avoids duplicating portfolio dispatch and changing old `--json` behavior.

Move each target into one mutable `Problem.target` for each branch. Do not clone the net, write branch JSON files, or spawn a new Rust process per branch. The parser already computes expressions sparsely and materializes dense final constraints only once per comparison.

## Deadline and aggregation

Capture the whole-property start before file reads and parsing; use a checked finite deadline. At each branch, compute the actual remaining duration. Start with the existing deterministic equal-share rule `remaining / remaining_branches`, carrying unused time forward. Existing engine checks are cooperative, so the outer cgroup/process-tree timeout remains authoritative. Never reset the whole-property deadline per branch. If parsing consumes the budget, emit `unknown` without starting a solver. Discard a newly returned definitive result after the whole-property deadline. A partial output killed by the outer runner is also `unknown`, even if a proof appeared during shutdown grace.

The in-process scheduler cannot forcibly terminate an individual library call like the Python subprocess wrapper did. An engine exceeding its advisory branch share can consume subsequent shares; recompute from actual elapsed time and enforce the property deadline. This is a declared scheduling change in a new candidate, not a performance-equivalent reimplementation of the frozen frontend.

Branch order is parser DNF order and branch indices are zero-based. A checked reachable branch establishes existential reachability; stop immediately. Unreachability requires every branch to be refuted, including branches whose target is an empty conjunction. An empty branch list is logically false and therefore unreachable, but the independent checker must confirm that the original property really has no branches. Any unknown or unattempted branch prevents an unreachable answer. Parsing/unsupported-input failures are errors, never negative answers.

`verdict` always describes the EF target or AG counterexample target. Derive `property_truth` only for a definitive verdict:

```text
EF reachable -> true       EF unreachable -> false
AG reachable -> false      AG unreachable -> true
```

Do not invert individual proof meanings for AG; invert only the final property truth.

## Compact output and independent checking

Return one typed JSON object, serialized directly with `serde_json::to_writer`, rather than constructing large intermediate `serde_json::Value`s:

```text
{
  "kind": "original-property-v1",
  "property_id": "...", "property_kind": "EF",
  "branch_count": 3,
  "verdict": "reachable", "property_truth": true,
  "parse_seconds": ..., "solve_seconds": ...,
  "attempts": [
    {"branch": 0, "outcome": <existing Outcome>},
    {"branch": 1, "outcome": <existing Outcome>}
  ]
}
```

This carries the actual branch certificates/witnesses without duplicating the original net or target vectors. Unknown attempts may retain normal diagnostic fields; avoid embedding `Problem`. Keep proof emission inside the measured invocation. Large proof output has a real cost and must not be silently excluded.

The benchmark parent independently parses original PNML/XML using `native_original.translate`, **outside the measured interval**, or loads the already hash-checked canonical branches. It then:

1. Checks the requested property ID, polarity, and total branch count against its independent translation.
2. Checks attempt indices are unique, in range, and in the declared order; rejects malformed verdicts.
3. Replays each positive witness against the independently reconstructed original net and that canonical branch. Checks every negative certificate against the corresponding canonical branch with `benchmark.verify`.
4. Recomputes the aggregate verdict/truth from checked results and complete branch coverage; does not trust the frontend’s aggregate fields.
5. Treats an unsupported proof or checker failure as unchecked/error, not a verified negative. No proof-free finite-state exhaustion claim becomes trusted merely because Rust emits it.

**This validates the original answer without serializing the translated net.** A parser bug that changes the internal query cannot manufacture a valid witness/certificate for the independently reconstructed original query. It may cause an unknown or a checker rejection. Full translation equality is a separate parser-validation claim, not something an output header or same-process hash proves.

For regression/debug audits, an optional future `--export-query PATH` can emit `{net, property_id, kind, targets}` **once**, outside benchmark runs, and exit after parsing. Compare this object with Python’s independent translation. This costs O(net + all targets), rather than serializing the entire net once per disjunct. Default timing runs need no export. Existing frozen input hashes and recorded command paths identify the bytes consumed; a new ad hoc fingerprint format is unnecessary.

## Integration gates after collection

- Register `pnml` and extract dispatch without changing existing methods or defaults.
- Add CLI tests for exact ID selection, EF/AG polarity, empty target/disjunction, a first unknown followed by reachable, all-negative complete coverage, partial-negative coverage, malformed property, and incompatible flags.
- Give the branch runner an injected clock/solver in unit tests so shared-deadline behavior is tested deterministically without sleeps.
- Extend the Python benchmark adapter with a separately named Rust-original mode; leave frozen binaries/frontends intact. Capture all new source hashes and the selected input scope.
- Test every certificate family through the original-input path and prove that a forged branch index, branch count, polarity, or aggregate verdict is rejected.
- Measure on development or newly frozen training data only after correctness gates. Treat frontend savings as engineering evidence, not algorithmic novelty, and preserve the harder-benchmark work as the current priority.
