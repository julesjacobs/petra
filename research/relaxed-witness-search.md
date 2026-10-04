# Relaxed prerequisite guidance

`--method relaxed` searches exact sparse markings while using a delete-relaxed prerequisite graph to order states. Every positive answer is replayed on the original net. Exhaustion, heuristic failure, arithmetic overflow and resource limits return unknown. This engine supplies no negative proof.

Facts are weighted input guards `m[p] >= w`. A transition with positive net effect on a place offers those facts at the maximum cost of its prerequisites plus an estimated repetition count. Signed linear target constraints select an improving transition; backward traversal through cheapest guard achievers identifies helpful enabled actions. Lazy evaluation, deeper-state tie preference and periodic FIFO expansion combine goal guidance with alternate exploration. Heuristic arithmetic saturates; successor arithmetic is checked. Neither scores nor relaxed dead ends are used for proof or state pruning.

Sorted nonzero `(place, count)` pairs are shared between node storage and the visited set. Successors retain exact guards and original transition indices. The independent Python witness checker remains required by the measurement harness.

`--method portfolio-relaxed` retains the causal portfolio's initial arithmetic stage (20% of the supplied budget, capped at 500ms), then gives the relaxed search 60% of the remaining budget and the existing portfolio the remainder. `portfolio-causal` and the default `portfolio-v2` keep their existing schedules. This initial allocation is a proposal to measure, not an established optimal schedule.

The implementation is motivated by independently replayed VerifyPN development witnesses with long target-place plateaus; it does not use competitor witnesses at runtime. Delete-relaxed planning and preferred operators are established techniques. No novelty claim is made.

Seven targeted tests include weighted guards/read arcs, a distracting unbounded target plateau, signed/equality goals, relaxed resource reuse that must not produce a false witness, large sparse counters, limits/overflow, and 80 bounded-net differential cases. Competitive performance is unmeasured until the recorded comparison completes.

Independent read-only review found no soundness blocker. Current limitations include aborting successor generation as soon as the state cap is reached, equal-depth/equal-score FIFO ties, and coarse internal deadline polling in some initialization/heuristic loops and replay. The whole-property outer deadline is still required. These are candidates for measured ablations, not changes made to the frozen first comparison.
