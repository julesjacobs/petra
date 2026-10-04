# Mechanisms suggested by the expanded input structure

This is source and input inspection during the frozen full comparison. No new
solver run, timing experiment, or production edit supports these proposals.
The current comparison must finish before selecting implementation work.

## The new inputs change the acceleration question

The previous survivor models have small certified total-token bounds. Three new
families instead start with genuinely large markings on small nets:

| Larger selected model | Places / transitions | Initial total | Largest initial place |
|---|---:|---:|---:|
| MAPK-PT-10240 | 22 / 30 | 46,080 | 10,240 |
| HouseConstruction-PT-32000 | 26 / 18 | 32,000 | 32,000 |
| ClientsAndServers-PT-N5000P0 | 25 / 18 | 85,000 | 40,000 |

These are observed initial counts, not certified global place bounds. Their
transitions can increase unweighted total tokens. Thus the old boundedness
argument against very large fixed-word repetitions does not transfer with the
same numerical limits. MAPK's RC06 target requires draining all 10,240 initial
Raf tokens; only reaction k1 consumes Raf, so every witness needs at least
10,240 occurrences of that transition alone. Existing fixed-8192 count discovery
cannot propose such a witness. The combined portfolio also has a larger-budget
count stage and batched singleton search, so this observation is not a claim
that it necessarily fails.

Existing `repeat_fire` and `relaxed-batched` already accelerate single-transition
blocks. `scheme_search` instead enumerates fixed word sequences; the Python ABMC
driver restarts Z3 at each bound. A new claim about acceleration therefore needs
comparison against the existing singleton batching and a persistent ordinary
BMC control. Positive compressed witnesses already have independent Rust and
Python checking utilities, but their integration into the main original-input
portfolio remains separate work.

## First candidate: exact scheduling for acyclic transition dependencies

Both HouseConstruction models have an acyclic producer-to-consumer transition
graph (18 vertices, 24 edges). Both NQueens models have no producer-to-consumer
edges at all: their four consumed resource places are distinct from their
unconsumed result places. This structural observation was checked on the first
canonical branch of each exact imported model; no property truth was inferred.

Put an edge `s -> t` whenever `s` produces a place consumed by `t`, retaining
self-edges caused by read arcs. If this graph is acyclic, every nonnegative
integer state-equation solution is executable by firing each transition's whole
count in topological order. At a transition's turn all producers of its inputs
have completed. Nonnegative final marking ensures the remaining tokens cover
the total requirements of all remaining consumers, hence this transition's
entire block. This argument preserves weighted arcs; the acyclicity condition
excludes read arcs rather than silently ignoring them.

This yields a narrow, complete realization rule: obtain exactly checked integer
counts, sort the original dependency graph, and check at most one repeated block
per transition. Use the existing compressed-word checker. A failed bounded count
query still means unknown; global negatives require an actual arithmetic proof.
The current `dag-sat` method concerns an acyclic one-token *control projection*,
so it does not already implement this different structural condition.

This is established structure, not a novelty claim. Its potential benefit is
removing dependence on expanded witness length in a natural new workload.
Promote it only if the completed comparison identifies count realization or
expanded witness handling as a material gap. HouseConstruction has only 18
transitions; the arithmetic model itself should remain small.

## Second candidate: combine grouped excess with full target conjunctions

The current grouped-excess solver rejects a property only when one target row
alone exceeds its closed-form bound. It discards information useful when rows
conflict jointly or when the original state equation constrains correlations.
For an independently checked invariant `sum_g max(M_g-h_g,0) <= B`, introduce
nonnegative auxiliaries `e_g` and the linear constraints

    e_g >= M_g-h_g,       sum_g e_g <= B.

Conjoin these with the original state equation and all target rows, and use an
exactly checked Farkas refutation. This extended formulation is exact for the
invariant sublevel set; it requires only one auxiliary per group, rather than
enumerating every subset inequality. The proof wrapper must verify grouped
induction before admitting these rows and reconstruct every coefficient from
the original net. A feasible relaxation remains inconclusive.

If lack of an unweighted invariant is the actual obstacle, a later extension
can synthesize nonnegative rational group weights `lambda_g`. The already
derived per-transition maxima `U_tg` give linear sufficient conditions
`sum_g lambda_g U_tg <= 0`. With signed row coefficients summarized as
`alpha_g=max(0,max a_p)`, requiring `lambda_g >= alpha_g` gives target upper bound
`sum_g alpha_g*h_g + sum_g lambda_g*max(M0_g-h_g,0)`. Thus discovering a weighted
invariant that excludes a row is a small linear feasibility problem for a fixed
partition and thresholds. Exact reconstruction and original-arc checking remain
mandatory; template failure says nothing about reachability.

Both changes preserve the new successful guard-aware invariant mechanism.
Neither has measured additional coverage. Do not tune partition/threshold
variants merely because they are easy to enumerate.

## Major engine direction

ASLink and Railroad are the new wide sparse nets: the larger instances have
4,410/5,405 and 1,018/10,506 places/transitions respectively. Their initial
coordinates are zero or one, but this does not prove 1-safety. Together with
the remaining RERS survivors they remain plausible decision-diagram workloads.
First qualify ITS on original properties. If it demonstrates substantial
complementary coverage, an exact MDD kernel should preserve signed targets,
read guards, compressed negative closure checking and original-transition
witnesses. A dense numeric domain expansion is particularly risky on MAPK and
ClientsAndServers. One representation need not be optimal for both regimes.
