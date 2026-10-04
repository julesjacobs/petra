# Frozen integration review

Reviewed `research/grouped-excess-repeat-20261004/snapshot/src` on 2026-10-04. No actionable issues found in the reviewed integration.

Scope: CLI default and raw-input compatibility; original-property branch scheduling; `portfolio-excess` stage ordering and budget accounting; guided-walk enabledness and witness replay; scaled-search lifting; reduction proof directions and recursive verification. Also inspected the corresponding CLI regression tests.

- `auto` selects `raw-potential` for raw input and `portfolio-excess` for ordinary input. Raw dispatch preserves its existing accepted methods.
- The original-property scheduler accepts a positive answer from any branch and requires negative answers from every branch. It accounts for parsing and actual elapsed time and rejects late results.
- Initial-marking, grouped-excess, scaled guided-walk, and guided-walk stages precede optional target reductions. Subsequent stages receive the remaining elapsed-time budget.
- Scaled search lifts only positive answers. Repeating a scaled witness is valid by monotonicity, and the expanded trace is checked on the original net. Guided-walk answers also require original-net replay.
- Reduction wrappers lift positive witnesses and preserve the required direction for negative proofs. The recursive verifier recognizes the added proof kinds.

This was a source-only review. No builds, tests, solvers, or benchmarks were run, and the frozen source and running campaign were left untouched. Witness replay remains non-interruptible internally; callers enforce hard wall limits and reject late answers. That known resource limitation does not change the reviewed proof directions.
