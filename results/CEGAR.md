# CEGAR experiment

The explicit threshold CEGAR prototype adds no solved query to the existing portfolio at the two-second budget. The default portfolio remains unchanged.

| Method | Reachable | Unreachable | Unknown | Solved |
|---|---:|---:|---:|---:|
| Threshold CEGAR | 13 | 140 | 65 | 153/218 |
| Existing portfolio | 14 | 197 | 7 | 211/218 |
| Portfolio with CEGAR | 14 | 197 | 7 | 211/218 |

One repetition; sequential cold processes; 2 seconds and 200,000 states per query. There were no errors or conflicting definitive verdicts. All 140 CEGAR unreachability certificates passed independent Python closure checking, and all 13 positive traces passed independent replay. The two portfolios agreed on every query, including all seven unknowns. No speed or record improvement is established by this experiment.

The full raw run and source/binary hashes are in [cegar-comparison](cegar-comparison/REPORT.md). The earlier [focused run](cegar-residual/REPORT.md) also left the seven residuals unresolved. The initial threshold-1 diagnostic is preserved in `cegar-residual-initial`; the final implementation starts at threshold 2 so zero and one tokens remain exact.

## Implemented scope

The engine uses finite threshold abstraction, explicit abstract-state BFS, concrete path replay, and counterexample-driven threshold refinement. It exports an independently checkable abstract closure for negative answers. The experimental portfolio combines it with the existing arithmetic, trap and support refuters.

This is **not** the full proposed symbolic/arithmetic generalization: it has no BDD/MDD saturation, residue predicates, relational predicate learning or accelerated path validation. Arithmetic and structural refuters are portfolio stages rather than sources of predicates for the abstraction. The results concern only this threshold prototype. They neither establish nor rule out gains from the broader proposal.

The next useful extension would be to preserve relational invariants in the abstract state space and measure whether this reduces the residual graphs. Merely replacing the explicit set with a decision diagram may compress those graphs, but would not fix spurious paths caused by missing correlations. Neither benefit has been independently measured here.

## Checks and limits

64 Rust tests passed, including 180 bounded differential cases for CEGAR; one pre-existing artifact-dependent test remains ignored. Clippy passed with warnings denied. Ten independent Python certificate tests passed. Tests include high-bucket decrement exits, read arcs, signed/equality targets, refinement and forged certificates.

The corpus contains 218 exported backend queries from the paper artifact, rather than all disjuncts of all paper benchmarks. These are backend-only results, with proof checking outside the timed solver. Timings are exploratory and not isolated-machine measurements. The previously measured SMPT baseline solved 210/218 at two seconds; the full SMPT corpus was not rerun in this experiment.

See [implementation and proof semantics](../research/cegar-implementation.md).

## Larger-budget residual experiment

At 5 seconds and 500,000 states, CEGAR still solved none of the seven residual queries. The existing portfolio solved four by BFS, with independently replayed witnesses:

| Query | Expanded states | Witness length |
|---|---:|---:|
| e2_disjunct_0 | 253,955 | 26 |
| e3_disjunct_2 | 231,498 | 15 |
| g1_disjunct_0 | 256,673 | 15 |
| g3_disjunct_1 | 215,242 | 13 |

Every successful search expanded more than the earlier 200,000-state cap. Both the time and state budgets changed, so this is not an isolated measurement of either parameter. `c1_disjunct_0`, `e4_disjunct_2` and `g2_disjunct_1` remained unknown. See the [larger-budget results](cegar-residual-long/REPORT.md).

SMPT was rerun on the same seven queries with a five-second limit and left all seven unknown. Thus the four new BFS witnesses extend coverage over this matched-time SMPT run. This is a focused backend comparison, not a claim about end-to-end paper performance or a general reachability record. See [SMPT residual results](cegar-residual-smpt/REPORT.md).

A full-corpus confirmation at 5 seconds and 500,000 states solved **215/218** with the existing portfolio: 18 reachable, 197 unreachable and 3 unknown, with no errors. All 215 definitive results passed independent Python verification. These gains come from the larger BFS budget, not CEGAR. See [the full larger-budget run](portfolio-larger-budget/REPORT.md).

```sh
./target/release/vass-reach --json problem.json --method portfolio \
  --seconds 5 --max-states 500000
```
