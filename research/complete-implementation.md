# Complete native Kosaraju procedure

`--method kosaraju` now runs a generalized-VASS decomposition procedure in Rust. This is separate from the earlier bounded `klm-schemes` search and does not invoke KReach, Z3, or another external solver. The ordinary portfolio tries it after the other engines if time remains.

```sh
cargo build --release --locked
./target/release/vass-reach --json problem.json --method kosaraju --unlimited
./target/release/vass-reach --json problem.json --method kosaraju --seconds 2
```

`--unlimited` removes time, row, node, and state budgets. The underlying decision procedure terminates on finite inputs under the usual unbounded-memory model. This is a new implementation of the complete algorithm, not a formally verified implementation; physical memory/address-space exhaustion remains possible. Without `--unlimited`, all resource exhaustion returns `unknown`.

## Algorithm

The implementation follows the generalized-VASS presentation in [Lasota, VASS reachability in three steps](https://arxiv.org/abs/1812.11966), with the missing implementation details made explicit in [complete-spec.md](complete-spec.md).

1. Reduce the conjunction of signed linear target constraints to exact point reachability. Preserve pre/post overlap by splitting such transitions through private control states. Disjoint pre/post support is already a pure effect and needs no split. Exact point targets use a smaller direct encoding.
2. Prune graph states that cannot lie on an entry-to-exit path, normalize coordinates with a known constant value, and enumerate SCC paths. Never replace a free constant-valued coordinate by zero.
3. Build the global characteristic equations over nonnegative edge counts and free endpoint values, with fixed endpoint values substituted. Include flow conservation, counter effects, and mandatory links between components. Counts are allowed to be zero.
4. Decide integer feasibility exactly. Primitive integer equality elimination catches divisibility contradictions; exact rational elimination and bounded integer branching decide the remainder. The finite existential bound follows from the Steinitz rearrangement lemma, not a user-selected search bound.
5. Test whether every edge count and every free endpoint coordinate is unbounded, using exact nonnegative homogeneous rays. If a variable is bounded, derive its finite maximum by exact rational feasibility and enumerate all allowed values. A bounded transition is replaced by copies of the graph with that transition removed, separated by mandatory occurrences of the transition, with correct entry/exit states.
6. Test forward and backward pumping on the constrained-coordinate projections using ancestor-based Karp–Miller trees. When pumping fails, extract a pathwise bounded-coordinate bound. Enumerate endpoint values or unfold a bounded coordinate into finite control states, make it rigid, and add an adjustment component to preserve the original final marking and outgoing link.
7. Accept a sequence when both conditions hold. Reject only after the entire finite refinement search is exhausted. Each refinement is checked against the strict lexicographic component rank `(nonrigid coordinates, internal edges, free endpoints)`; its multiset extension supplies termination.

All counter, equation and bound arithmetic uses arbitrary-precision integers/rationals. There is no hidden word-length cutoff in this procedure.

## Witnesses and refutations

After the sufficient conditions establish reachability, an exact BigInt BFS on the original net extracts a firing sequence, which is replayed using BigInt arithmetic. This additional extraction terminates for proved-reachable inputs in unlimited mode, but can be expensive. A timed run that proves reachability but cannot extract a witness within its remaining budget conservatively returns `unknown` with that reason. Final markings exceeding u64 are serialized as decimal strings in a `big-witness` proof object.

An unreachability result records exhaustion of the decomposition search. It does **not** yet export a separately checkable decomposition proof tree. The standalone `--verify` command checks witnesses and the existing arithmetic/structural certificates; it does not independently verify a Kosaraju negative result. Such benchmark results must be labelled accordingly.

## Validation

Tests cover the external implementation's read-arc and multiple-control-state counterexamples, parity, omitted transitions, empty components, linked free rigid-looking coordinates, forward/backward pumping, bounded-coordinate unfolding with a following link, zero budgets, unlimited mode and counters larger than u64.

Differential checks compare all six final configurations of 30 bounded finite-control VASSes (180 cases) and 36 signed linear-target conjunctions with exhaustive reachability. Arithmetic tests independently enumerate 539 bounded integer systems. These tests substantiate the implementation but do not constitute a formal correctness proof.

## Measured results

All 54 Rust tests and Clippy pass. The CLI unlimited-mode read-arc smoke test produced a replayed one-step witness and passed `--verify` (`research/complete-cli-smoke.json`, `research/complete-cli-answer.json`).

On all 218 collected SER queries with a two-second budget, standalone Kosaraju proved 186 unreachable and returned 32 unknown; it found no reachable cases within that budget. The portfolio retained 211 solved (14 reachable, 197 unreachable), with seven unknown. There were no conflicting definitive verdicts or execution errors. This is one pass, with other compiler workloads active; negative Kosaraju results are not independently certified. Raw inputs, source/binary hashes, logs and results are in [the report](../results/complete-comparison/REPORT.md).
