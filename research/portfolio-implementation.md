# Rust portfolio implementation and evaluation

The native solver remains incomplete. This implementation adds exact integer-cut refutation, structural invariants and repeated-word acceleration; it does not implement full KLMST decomposition/refinement. The external KReach build supplies a Kosaraju-family experiment and is never called by the Rust portfolio.

## Arithmetic

Rational elimination now substitutes detected exact equalities and discards weaker parallel inequalities before enforcing the row limit. Its Farkas certificate format is unchanged. Integer elimination divides each inequality by the gcd of its coefficients and rounds its lower bound upward, with four deterministic elimination orders. Every step is recorded in a dependency DAG and replayed in Rust and independent Python integer arithmetic. A feasible projection remains unknown; the procedure is not a complete integer-programming solver.

This resolves the six arithmetic gaps diagnosed earlier: two rational cases previously exceeded the row limit, and four require integrality.

## Structural invariants

Marked-trap enumeration adds inequalities saying an initially marked trap remains nonempty. The verifier checks the initial marking and the pre/post structural condition, then verifies a Farkas contradiction against the augmented target. This resolves e1_disjunct_0 and e7_disjunct_0.

Support closure identifies an initially empty siphon and constrains its final sum to zero. It provides no additional solved SER queries in the ablation; it remains a separately testable engine.

## Accelerated positive search

The path-scheme engine summarizes words of up to four transitions by their exact minimum enabling marking and effect. It selects repetition counts at target boundaries, next-transition enabling thresholds and powers of two. Search alternates heuristic and FIFO work; unit transitions remain present. Witnesses are expanded (at most one million transitions) and replayed. Resource limits return unknown. Finite exhaustive exploration may prove unreachability.

This is bounded path-scheme search, not generalized-VASS decomposition or a complete KLMST procedure. It demonstrates acceleration on a 10,000-token two-transition test but adds no unique solved SER query over BFS in the ablation.

## Scheduling

The initial portfolio gave a short BFS pass at most 10,000 states. The ablation found c5_disjunct_0 via standalone BFS after 35,500 states, so the final schedule adds a second BFS pass after arithmetic. Each stage receives the smaller of remaining time and its budget fraction: initial BFS 5%, integer arithmetic 20%, marked traps 15%, support 10%, second BFS 25%, then accelerated search receives the remainder. Early completion does not waste the remaining budget.

`results/portfolio-ablation` preserves the initial schedule and binary hashes. `results/portfolio-comparison` measures the revised schedule in three repetitions against SMPT. Other compiler workloads were active on this host: timings are exploratory, and coverage is limited to 218 exported backend queries, not end-to-end SER execution.

## Checks

27 Rust tests pass; the artifact-dependent six-gap regression passes separately. Clippy passes with warnings denied. Tests include exhaustive bounded random nets, signed linear targets, weighted/read arcs, exact word requirements, parity and forged certificates. The Python benchmark checker independently verifies witnesses, integer/Farkas/structural certificates and finite closures. The target-to-point adapter (including atomic transition splitting) agrees with independent exhaustive reachability on 150 signed-conjunction instances.
