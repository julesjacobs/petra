# Threshold CEGAR prototype

`--method cegar` explores a finite abstraction of Petri-net markings. Each coordinate has exact values `0..k-1` and one interval `[k,infinity)`. The initial threshold is 2, preserving exact zero/one control tokens. The transition relation computes interval images independently per coordinate, preserving preconditions and read arcs. A decrement from a high bucket includes every possible exact exit and the remaining high bucket. The Cartesian product is enumerated incrementally.

Target feasibility uses exact arbitrary-precision interval bounds on each signed linear constraint. Equality checks both endpoints. Conjunctions may admit spurious targets because correlations between constraints are discarded; this is an overapproximation, so it cannot produce a false negative.

When BFS reaches an abstract target, the engine reconstructs its transition sequence and replays it concretely. A replayed witness is checked against the original target. A spurious path increases thresholds to make values visited in its concrete prefix exact, at least doubling affected thresholds. When none of those coordinates requires splitting, all thresholds double. Search restarts after refinement. This is deliberately a simple refinement heuristic; it does not guarantee the same spurious suffix disappears in one round.

A closed abstract reachable set excluding every abstract target proves unreachability. Negative answers export `threshold-closure-v1` with thresholds and the closed set. The Rust standalone verifier and independent Python benchmark verifier check the initial state, target exclusion and **all** abstract successors. They need not trust the solver's reachability computation. Positive answers export firing sequences. Resource limits and counter/threshold overflow return unknown.

This is an explicit-state CEGAR prototype. It does not implement BDD/MDD saturation, residue predicates, learned relational predicates, or accelerated path validation. It is not a replacement for the complete Kosaraju procedure. The proposed general symbolic/arithmetic engine remains future work; these experiments measure only threshold abstraction.

`--method portfolio-cegar` keeps the default portfolio's BFS, integer equation, traps, support and second BFS stages, then substitutes CEGAR for the repeated-word acceleration stage. Both versions can use any remaining time for Kosaraju. The default `portfolio` schedule is preserved for comparison. Arithmetic and structural stages are independent refuters; their invariants are not yet incorporated into the abstract transition system.

## Verification

The Rust tests include 180 bounded differential comparisons against explicit BFS; adversarial tests cover decrements leaving high buckets, enabling above thresholds, read arcs, signed/equality targets, incompatible conjunctions, refinement, resource exhaustion, and forged closures. Independent Python tests cover the same certificate boundary with arbitrary-precision arithmetic.

The solver checks deadlines during graph exploration, successor enumeration, trace reconstruction and concrete replay. Final witness checking and JSON serialization can run beyond the deadline; benchmark processes also have an outer timeout. `--max-states` bounds both cumulative expanded states and the number of stored states in any round. A successor-state limit can therefore be reached before the reported expanded-state count reaches the limit.
