# Accelerated BMC prototype

Implemented an experimental Rust encoder and exact compressed witness checker in
`src/accelerated_bmc.rs`, exercised through `examples/accelerated_bmc.rs`.
This is not integrated into any portfolio and has no competitive performance result.
The backend for the encoding is explicitly external Z3, not our native SAT engine.

## Encoding

Fix a finite vocabulary of transition words and a bound on the number of segments.
Each segment chooses a word and a nonnegative integer repetition count. Markings
and repetition counts are mathematical integers. Every marking is nonnegative.
Zero repetitions are the identity, including when the chosen word is disabled.

A word has an exact enabling vector h and effect d, computed by composing the
original weighted consume/produce transitions. For count n > 0 and entry marking m,
its enabling condition in coordinate p is

    m[p] >= h[p] + (n - 1) * max(-d[p], 0).

Its exit marking is m + n*d. Because h and d are constants for each chosen word,
this is quantifier-free linear integer arithmetic. The guard covers every internal
transition of every repetition, including read arcs. The implementation reuses
`WordSummary`; it does not infer enabling from net effects alone.

The final marking satisfies the original signed linear inequalities/equalities.
A satisfying assignment is decoded to original transition words and decimal
repetition counts. The Rust checker recomputes summaries from the original net,
checks every segment, and checks the original target with arbitrary-precision
arithmetic. No expanded firing trace or u64 intermediate marking is required.

UNSAT or unknown at the requested vocabulary/depth supplies no global negative
answer. With all singleton transitions in the vocabulary, increasing segment
depth includes every finite execution eventually, but supplies no termination
argument for unreachable targets. Neither acceleration nor this encoding is
claimed novel.

## Evidence

- Four Rust tests pass, including exhaustive small single-transition prefix replay,
  internal read guards, arbitrary-precision counts, signed targets and malformed models.
- The existing four summary/backward tests pass.
- `research/check-accelerated-bmc-prototype.py` passes 66 real Z3 5.1.0 queries:
  63 bounded transfer-net queries checked against independent exhaustive search;
  a disabled repeated word; a one-trillion-firing witness; and depth-zero reachability.
- All 51 satisfying models also pass an independent Python compressed checker.
  That checker checks each original transition's guard at both extreme repetition
  indices rather than invoking the Rust summary implementation.
- Bounded UNSAT is exercised and remains `unknown` at the reachability API boundary.

Artifacts: `accelerated-bmc-prototype-check.json`, test/build/check logs, and source.
These are correctness-oriented prototype checks, not benchmark measurements.

## Next experiments

Implement automatic, budgeted vocabulary discovery rather than requiring a supplied
word list. Start with singleton acceleration as a separately measured ablation;
then discover recurrent words from search traces/control structure, retaining all
singletons. Compare ordinary BMC, singleton acceleration and discovered-word
acceleration at matched whole-property budgets against frozen controls. Record
encoding construction, solver and independent-checking costs separately and total.

The prototype currently builds the full formula in memory and requires an external
process wrapper for deadlines/memory. Before benchmark integration, bound encoding
work and output, preserve solver errors distinctly, add compressed witness support
to the existing independent benchmark checker, and freeze the complete pipeline.
Do not promote it based on the synthetic trillion-step example alone.

Targeted Clippy passes after replacing one unnecessary test clone; changed-file
format checks pass. Pre-existing warnings in vendored varisat remain. The initial
Clippy failure and successful rerun are both retained.

## Subsequent implementation

Automatic bounded dependency-cycle discovery, ordinary-BMC ablation, sparse
encoding, a whole-query deadline driver, and an independent compressed checker
are now implemented. See `accelerated-bmc-discovery-v1-report.md` for tests and
the complete111-row classical mechanism screen. The original manually supplied
vocabulary API remains available. Production integration and competitive evidence
remain outstanding; the "Next experiments" list above records the initial plan.
