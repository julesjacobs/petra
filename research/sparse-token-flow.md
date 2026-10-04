# Sparse token-flow master and shared candidate scaling

Completed the scope in `sparse-token-flow-handoff.md`. Implementation changes are confined to `src/token_cut.rs`; differential integration tests are in `tests/sparse_token_master.rs`.

`token_cut::master` constructs transposed place incidence from actual weighted pre/post arcs and mode conservation from edge endpoints. It no longer scans every place or mode against every edge. Stuttering endpoints contribute nothing. Exact coefficient ordering, row ordering, and negative-then-positive equality rows are preserved. Zero target coefficients are omitted. Checked dimension addition, the 100,000-variable and 100,000-mode limits, problem validation, and graph-coordinate checks reject invalid inputs.

`solve_with_bounds` computes the checked common denominator and integer candidate once per candidate, then reuses them for every place. Public standalone separator signatures are unchanged. Cut violation is checked exactly using integer arithmetic, equivalent to the original rational inequality. Negative candidates, deadlines, and the 4096-bit denominator limit remain checked; numerator magnitude is unrestricted.

## Validation

| Command | Result | Log |
| --- | --- | --- |
| `cargo test --locked --test sparse_token_master --test token_cut --test bounded_token_cut --test token_flow` | 21 passed | `sparse-token-flow-focused-tests.log` |
| `cargo test --locked --lib token_cut::scaling_tests` | 3 passed | `sparse-token-flow-scaling-tests.log` |
| `cargo test --locked` | 324 passed, 0 failed, 1 pre-existing ignored | `sparse-token-flow-full-tests.log` |
| `cargo clippy --locked --all-targets -- -D warnings` | Passed | `sparse-token-flow-clippy.log` |

The first Clippy run identified two new test expressions using `% n == 0`; both were changed to `.is_multiple_of(n)` before the successful run. Existing vendored Varisat warnings remain.

The independent dense-master oracle compares complete exact rows for all terminal modes of weighted, read, source, sink, stuttering, and control fixtures, including interleaved data/control indices, disabled two-control transitions, `u64::MAX` arcs, and signed targets including `i64::MIN`. Corresponding rows also agree with unchanged `token_flow::relaxation`. Edgeless controllers, unreachable control places, and invalid coordinates are covered.

Shared-scaling unit tests perform 432 shared-versus-standalone separation comparisons across rational candidates and bounded/unbounded cases, rechecking returned cuts with rational arithmetic. They cover expired deadlines, invalid inputs, nonconservation, negative candidates, exactly 4096-bit denominators, oversized individual/combined denominators, and large numerators.

The new debug binary also verified three existing saved answers, each with exit code 0 and `{"verified":true}`:

```text
target/debug/vass-reach --json results/portfolio-larger-budget/g2_disjunct_1.json --verify research/g2-token-cut.json
target/debug/vass-reach --json results/portfolio-larger-budget/g2_disjunct_1.json --verify research/g2-bounded-token-cut.json
target/debug/vass-reach --json research/bounded-cycle-problem.json --verify research/bounded-cycle-answer.json
```

These cover 12 token-cut terminal proofs, 12 bounded-token-cut terminal proofs, and 2 bounded-cycle terminal proofs. Output is saved in `sparse-token-flow-saved-proofs.log`.

`token_flow::relaxation`, proof formats, Python checkers, frozen artifacts, and remote files are unchanged by this task. No release build or benchmark was run, and no measured performance improvement is claimed.

All owned process handles are terminal. The final `process_runner.workspace_workloads` check returned `[]`. The local Cargo/build/test window is released to the coordinating agent. Further capacity integration and global benchmark work remain outside this scoped task.
