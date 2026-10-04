# Certified finite-counter token cuts

The `finite-token-cut` method generalizes the existing token-cut engine to finite projections of certified bounded counters. This is an incomplete solver: bounded discovery, projection selection, graph limits, LP search, and deadline exhaustion can return `unknown`.

## Shared algorithm and proof contract

`src/finite_control.rs` defines a graph view implemented by the legacy one-hot `Control` and the new `FiniteControl`. The view exposes selected original place indices, number of modes, initial mode, original transition edges, and exact selected coordinate values. The master, per-place bounds, scaled-candidate separator, witness realization, and terminal solve loop in `src/token_cut.rs` are shared. Legacy mode/edge order and row order are preserved.

The new certificate has exactly these fields:

```text
{kind: "finite-token-cut-v1", controls, bounds, terminals}
```

`controls` is sorted and unique. `bounds` is an existing `place-bounds-v1` certificate. Each terminal contains the existing `cuts: [{place, modes}]` and `multipliers` fields. No graph is trusted from the certificate. Rust reconstructs checked bounds and the entire graph before checking every terminal's exact Farkas combination. Positive results replay original transitions against original weighted guards.

Graph construction starts from the selected initial tuple at mode zero. It performs BFS, processing original transitions in original order at every mode. Selected pre-arcs must be enabled; selected post-arcs determine the successor. Successors exceeding certified coordinate bounds are omitted because those markings cannot occur on concrete runs. All enabled projection transitions, including read and stuttering transitions, are retained otherwise. Selected values and bounds must fit `u64`; bound subtraction prevents successor overflow. Graph construction rejects exhausted deadlines or limits instead of returning a prefix. Certificate reconstruction permits at most 4096 modes and 8192 edges.

An empty projection has one mode and one stutter edge per original transition, giving a state-equation fallback. At selected coordinates, each source moment is fixed to the source tuple value times its edge count, and each terminal marking is fixed to the terminal tuple. Unselected coordinates use the same checked finite-bound flow inequalities as the legacy bounded engine.

## Discovery and refinement

The solver combines metadata-free checked structural capacity proposals with existing LP-derived nonincreasing potentials. Both are rechecked against original weighted arcs. Discovery receives one fifth of the total timeout. Selection ranks bounded coordinates by target occurrence, then adjacency to target places, then domain size and original index. A bounded heap retains at most 4096 candidates; selection also has a deadline and a two-million-operation budget.

The solver first tries the empty projection, then progressively adds coordinates at prefix sizes 1, 2, 4, 8, and 16, including the final shorter prefix when applicable. Each attempt receives a share of the remaining budget. Selected domain products cannot exceed 4096; selection includes at most 16 coordinates even when some bounds are zero. Graph construction separately checks actual reachable modes and edges. An exhausted or oversized refinement cannot produce a negative answer. The shared solve loop checks its deadline before constructing a terminal master and while reconstructing cached cuts.

## Evidence

`tests/finite_token_cut.rs` compares graph modes and ordered edges against an independent explicit projection reference over all 16 selected subsets of a weighted four-place net. It compares full projections against original BFS, checks all small two-coordinate targets, checks all cut subsets and separators on concrete weighted/read/stutter walks, and exercises bounds, overflow, graph truncation, invalid coordinates, zero budgets, expired deadlines, malformed proofs, and CLI generation/verification.

The live cyclic fixture in `research/finite-token-cut-example-problem.json` has no one-hot controller. Independent original BFS finds exactly five markings and fires all five transitions. Projection onto `c,d` has tuples `(2,0),(1,1),(0,2)`. The counts `[1,2,1,1,1]` admit an unbounded moment model; a bounded `y` flow cut rejects it. The explicit bounded moment reference refutes every terminal. The generated answer in `research/finite-token-cut-example-answer.json` uses two selected coordinates, three terminal proofs, and two recorded flow-cut entries (including reuse between terminals). The coordinating agent reports independent Python verification passing both normally and under `python -O`.

Validation completed:

| Command | Result | Log |
| --- | --- | --- |
| `cargo test --locked --test sparse_token_master --test token_cut --test bounded_token_cut --test token_flow` | 21 passed | `finite-token-cut-legacy-tests.log` |
| `cargo test --locked --test finite_token_cut` | 9 passed | `finite-token-cut-focused-tests.log` |
| `cargo test --locked` | 334 passed, 0 failed, 1 pre-existing ignored | `finite-token-cut-full-tests.log` |
| `cargo clippy --locked --all-targets -- -D warnings` | Passed | `finite-token-cut-clippy.log` |

After the full run, Clippy identified a redundant target clone and two test-style lints. These were fixed, Clippy passed, and the nine focused tests passed again. Existing vendored Varisat warnings remain. The selection deadline/product/zero-bound-width regression is included in the full suite.

The current debug verifier accepts the existing `g2-token-cut.json`, `g2-bounded-token-cut.json`, and `bounded-cycle-answer.json` certificates, as well as the new `finite-token-cut-example-answer.json`. All four subprocesses exited 0 with `verified:true`; commands and outputs are in `finite-token-cut-saved-proofs.log`.

All owned process handles are terminal. The final workspace workload check returned `[]`; the local Cargo/build/test window is released to the coordinator. No further implementation work is assigned to this subtask.

No benchmark or release build was run for this implementation. No performance or completeness claim follows from these fixtures.
