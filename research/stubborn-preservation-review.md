# Witness-search reduction with bounded postponement

Status: design reviewed by the coordinator and portfolio_audit. Implementation
assigned; no performance result. This is a partial-order reduction technique,
not a novelty claim. Existing helpful-only search remains a heuristic.

Use the reduction only in the unrestricted fallback of relaxed-focused search.
Keep default engines, scheduling and limits unchanged, and expose an opt-in
ablation. Every positive answer still requires original-transition replay;
exhaustion and resource limits still return unknown.

## Closure at a marking

Let delta_t(p) be post_t(p) minus pre_t(p), with weighted arcs. Starting from a
seed, close a transition set S under these rules:

1. For enabled t in S, include every u such that some place p satisfies
   delta_u(p) < 0 and pre_t(p) > 0, or delta_t(p) < 0 and pre_u(p) > 0.
   Include u regardless of its current enabledness.
2. For disabled t in S, choose one deficient input guard m(p) < pre_t(p).
   Include every transition u with delta_u(p) > 0.

The second rule uses net-positive production; read loops do not enable a
deficient guard. The first rule is symmetric and includes readers, so it does
not confuse read arcs with the absence of an input guard.

Let A be the enabled members of the completed S. Use full expansion if A is
empty despite some enabled transition, if closure does not finish within its
resource limits, or if A equals all enabled transitions. For a proper reduction,
every transition in A must have zero delta on every place with a nonzero
coefficient in any target constraint. This suffices for arbitrary signed
inequalities and equalities; helpful actions alone do not justify omission.

## Preventing unbounded postponement

A finite-graph cycle proviso alone is insufficient: an independent invisible
source transition can generate infinitely many fresh counter values while
postponing a target-changing transition.

Use fixed discovery depth and a fixed K >= 1 (initial experiment: K=8). Fully
expand nodes whose depth is divisible by K. Also fully expand whenever ANY
chosen enabled successor was already globally seen before this expansion.
Check freshness against a pre-expansion snapshot, before inserting successors.
Every edge from a genuinely reduced expansion then creates a child at parent
depth plus one. Overflow forces full expansion or unknown. K=1 disables pruning.

Marking-only deduplication is compatible with these rules. Let d(m) be the
length of a shortest finite path from a target-reachable marking m to the target.
If such a shortest path contains S, its first S transition is enabled at m:
otherwise its chosen deficient guard cannot become enabled before an S producer
fires. Symmetric closure lets that transition commute to the front, producing
a chosen successor of strictly smaller d. If the path avoids S, any enabled
member of A commutes across the whole path; target invisibility gives a chosen
successor whose d is no greater.

At full expansion, the first edge of a shortest path strictly decreases d.
At reduced expansion with unchanged d, freshness advances discovery depth,
strictly decreasing (K - depth % K) % K. Thus the lexicographic rank consisting
of d and this remainder decreases along a suitable retained witness path.
A full step may merge into an old node with a different depth because d has
already decreased. The argument does not require a finite state space.

Fair queue exploration is required for eventual discovery without resource
limits. This argument establishes the reduction obligation, not completeness
of the existing bounded implementation or its helpful-only initial phase.

## Required adversarial checks

- An independent invisible source can otherwise postpone a visible finish
  forever; periodic full expansion must discover the finish.
- An invisible read/no-op loop has a seen successor and must force full expansion.
- An increment affecting an equality target is visible even if another target
  constraint needs progress elsewhere.
- Consuming a token needed by another transition's read arc requires symmetric
  dependence.
- Weighted deficient guards include all net-positive producers; sources,
  sinks, mixed pre/post arcs and zero-delta read loops are distinguished.
- Merging different discovery depths, closure interruption, depth overflow and
  K=1 must preserve the stated fallbacks.

Evaluate full 104-case development comparisons with POR off/on on the same
source and fixed budgets, including checked witnesses and state/transition
counts. Then test the full parent corpus for regressions. Reserved evaluation
families remain untouched. A state-reduction or coverage benefit is a hypothesis.
