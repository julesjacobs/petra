# Integrated reachability experiments

The new `portfolio-next` preserves the original `portfolio` for comparison. It tries a small BFS, the integer equation and marked traps, demand-source/eager-completion search, multi-queue search, count-plan refinement, backward-summary search, then quotient BFS. All stages share the wall-time budget. This is an experimental portfolio, not a claim of a new complete decision procedure.

## Engines

- `guided`: interleaves three queues using normalized target deficits, a target deficit excluding zero-equality cleanup, and weighted depth/deficit. A FIFO queue prevents heuristic starvation. No heuristic prunes a state. Sparse exact target evaluation and acceptance on generation avoid needless queue expansion. Ordinary finite exhaustion remains an exact negative answer.
- `quotient-bfs` / `guided-quotient`: retain counters read by transitions exactly. For counters never read, retain their contributions to each target constraint, preserving signed differences. A nonnegative contribution to a >= target can saturate at its bound only when the remaining coefficients are also nonnegative. These counters never decrease. Positives retain concrete representatives and replay original transitions. Quotient exhaustion returns unknown pending standalone closure certificates.
- `reduced-guided`: moves creation of private source tokens immediately before their consuming transition and private completion immediately after production. Restrictions are checked from arc structure and target usage, without matching benchmark names. It searches the transformed net and expands every returned transition into its original recipe. Only original-net replay may produce a positive answer. This engine never certifies a negative answer.
- `count-plan`: searches bounded native BigInt integer count models and checks forward/reverse support of the same candidate. Realization memoizes remaining count vectors. Forward support failure can exclude a support family through a covering disjunction; reverse support failure or exhaustive realization failure excludes only the precise count vector. Budget exhaustion does not justify a cut. Candidate infeasibility does not produce a global negative answer. Native exact elimination is currently a performance bottleneck.
- `backward`: exact BigInt word summaries contain the minimum enabling marking and the effect. Composition and fixed-word repetition are exact. A bounded beam computes symbolic target preimages; forward search meets those suffix regions and replays the concatenated trace. The beam is a heuristic underapproximation, never a global unreachability argument.
- `bounded-guided`: tries active-counter caps 1 through 4 using the quotient. This is explicitly an underapproximation; it returns only replayed positives or unknown. It is available for ablation and not included in portfolio-next.

No native engine invokes Z3. Decision diagrams, general PDR, LP-dual learning, and a full integrated Presburger relation are not implemented. Fixed-word summary repetition is implemented/tested, but the backward engine currently uses bounded words rather than solving parameterized accelerated suffix regions. These distinctions matter when attributing benchmark gains.

## Correctness boundaries

Original transitions and read arcs are preserved by replay. Bounded and heuristic searches never report negative answers from exhaustion. Arithmetic and trap negatives retain the existing exact certificates and independent Python checker. The new positive engines all emit ordinary original-net traces, checked both in Rust and independently in the benchmark harness. The sink-counter quotient does not saturate signed target differences or equality targets.

## Benchmark protocol

Compare all 218 artifact backend queries at two seconds and 200,000 states per native stage, three repetitions, alternating method order. Processes run sequentially. Input/source/binary hashes, cold-process timings, witnesses and proof results are saved. Both original portfolio and the artifact's SMPT STATE-EQUATION+BMC configuration are rerun. Timing remains exploratory on a shared host. This is neither an end-to-end frontend benchmark nor a claim against every SMPT strategy or external solver.
