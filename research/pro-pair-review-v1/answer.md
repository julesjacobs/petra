# Pro review: substantive answer

Source: https://chatgpt.com/c/6aba1a88-e75c-83ea-8b0d-2d137413267d
Observed complete on 2026-09-28, UI: “Worked for 42m 6s” and “Response complete”.
This is a faithful condensed transcription of the substantive answer, including
its qualifications, rather than a verbatim export. Review claims below are not
independently verified merely by being recorded here. See assessment.md.

## Recommendation

Keep phase-pair as a frozen useful baseline, but do not make first-event pair
closure the central research direction yet. Investigate a sparse,
property-directed invariant engine over signed integer-threshold predicates,
restricted to unary and binary clauses. The proposed contribution is effective
discovery, sparse dependency management, and independently checkable proofs
across weighted/unbounded nets—not predicate abstraction, induction, binary
clauses, or trace partitioning themselves. This is a research bet.

The reviewer inspected the supplied implementation and reports, but had neither
rustc nor cargo and did not build or run Rust. Original benchmark inputs/proofs,
the isolated frozen survivor runner, and pending full-cohort outputs were absent
from the supplied archive. The reviewer could not reproduce benchmark results.

## Pair-closure audit

The checked groups establish nonincreasing sums of places, initially at most
one, covering every place. These are sufficient structural safety proofs, not a
general safety test or necessarily conservation equalities. Each relation
contains all concretely occupied pairs in its trace phase; diagonals represent
possible individual occupancy. The phase records whether an event-set transition
has occurred. No assertion that an event must occur is needed.

Soundness follows from initial clique inclusion, overapproximated enablement,
conservative token survival, and preservation of surviving–surviving,
produced–surviving and produced–produced pairs. Pairwise compatible inputs need
not be jointly realizable; this loses precision, not soundness.

Skipping weighted pre-arcs above one is justified by proved safety. Skipping
weighted post-arcs above one is also justified: the checked group inequality
requires at least two consumed tokens in that group, impossible in any reachable
marking. Raw parallel arcs must first be aggregated. The Rust parser/model
boundary handles this distinction. Reads preserve their token but retain their
original guard. The explicit cross-phase transfer of unrelated surviving pairs
is present in both checkers and essential; a mutation omitting such a pair was
rejected by the reviewer probe.

The target test is sound but weak: a signed target row forces one place only
when all remaining positive coefficients sum below its bound. It handles widened
negation of i64::MIN. It cannot refute p+q>=1 when both places are permanently
empty, nor p=0 when p is permanently occupied. Computing positive-place necessity
before closure could reject inexpressible cases before allocating matrices.

The safety discovery heuristic unions all changing places. A synchronized move
`a0+b0 -> a1+b1`, initially a0=b0=1, admits the safe partition {a0,a1},{b0,b1},
but discovery merges all four and rejects mass two. The reviewer reproduced the
partition acceptance and grouping outcome in Python, not by running Rust.

Two validation findings:

1. Uploaded common scripts/benchmark.py lacks phase-pair-closure-v1 dispatch.
   Direct verify_phase_pair accepts a minimal proof, while common verify falls
   into the empty-siphon assertion. The reviewer explicitly acknowledges that
   the unavailable isolated frozen runner may already fix this; the finding does
   not invalidate the reported survivor checks. Add composition tests through
   bounded original-input validation and reduction wrappers in a new runner.
2. Python phase-pair validation checks target rows referenced by conflicts, but
   accepts an unreferenced row with a malformed coefficient dimension. Rust
   Problem::validate rejects it. Validate the complete problem schema first.
   This is an accepted-input-language mismatch, not a demonstrated false
   refutation of a well-formed problem.

Rust validation reuses Closure::pass; Python is implementation-independent.
Original PNML/XML binding additionally requires the original-input wrapper's
hashes, independent translation, branch identity and EF/AG aggregation checks.

Reviewer-reported probes: 400 small structurally safe nets, 1,200 net/monitor
configurations, 3,069 concrete phase states, 14,355 pair-target checks, 10,917
accepted negative certificates. Of 3,600 arbitrary certificates, 3,360 were
rejected; all 240 accepted certificates excluded unreachable targets. A ring(4)
probe had 30 concrete phase states and reproduced strict phase precision.
These are small correctness probes, not performance evidence or a proof of
implementation correctness. Their downloadable package was offered in the UI;
local download had not completed when this transcription was saved.

## Related work and novelty (reviewer claims)

- Haslum–Geffner h^m planning heuristics, especially m=2; describe this as
  delete-sensitive pair-reachability closure/mutex abstraction without equating
  all Graphplan details.
  https://www.ida.liu.se/divisions/aiics/publications/AIPS-2000-Admissible-Heuristics-Optimal.pdf
- Place concurrency/coexistency: Amat, Dal Zilio, Le Botlan.
  https://arxiv.org/html/2302.02686v1
- Trace partitioning: Rival–Mauborgne.
  https://www.di.ens.fr/~rival/papers/toplas07.pdf
- Incremental, Inductive Coverability: Kloos, Majumdar, Nikšić, Piskac.
  https://www.cs.yale.edu/homes/piskac/papers/2013KloosETALIIC.pdf
- Property Directed Reachability for Generalized Petri Nets: Amat, Dal Zilio,
  Hujsa. Central competition for weighted/unbounded linear-property reasoning.
  https://link.springer.com/content/pdf/10.1007/978-3-030-99524-9_28.pdf
- Petri Net Analysis Using Invariant Generation: Sankaranarayanan, Sipma, Manna.
  https://link.springer.com/chapter/10.1007/978-3-540-39910-0_29
- Houdini candidate elimination.
  https://link.springer.com/chapter/10.1007/3-540-45251-6_29
- On-Demand Mutex Constraints for Numeric Planning as SMT, ICAPS 2026. Action
  interference for bounded parallel planning, a different semantic object.
  https://ojs.aaai.org/index.php/ICAPS/article/view/42846
- Classical implication-graph 2-SAT.
  https://www.sciencedirect.com/science/article/pii/0020019079900024
- SMPT methods and PDR comparison.
  https://arxiv.org/html/2302.14741v1

Existing token_flow, token_cut, lazy_token_cut, finite_control, cegar,
local_closure, interval and linear modules already implement much of the older
Pro direction. Do not propose them as missing. The proposed new representation
is a sparse shared collection of relational clauses rather than another global
abstract marking product. Phase-pair currently allocates two dense matrices
under 2*n*ceil(n/64)<=8,000,000 words, limiting it to 16,000 places. The question
is whether relevant proofs remain small when full coexistency relations do not.

## Proposed signed-threshold induction

Atom P(a,k) means a.m>=k for exact integer a,k. Start with coordinate forms and
target normals. Invariants are conjunctions of one- or two-literal clauses,
with either polarity. Examples include absence mutexes, lower bounds such as
[x>=1] OR [y>=2], and conditional affine bounds. One mode first; a two-state
trace monitor is a later ablation. Finite vocabulary never bounds token values.

An original transition has guard m>=pre_t and update d_t=post_t-pre_t.
Pullback maps P(a,k) to P(a,k-a.d_t), preserving polarity. Original guards,
including zero-update read arcs, remain necessary. Integer negation is exact;
no clipping of thresholds or counters is permitted.

Build a Boolean implication graph using invariant clauses, units, and valid
same-form threshold order P(a,k2)=>P(a,k1) when k2>=k1. Nonnegative coordinate
thresholds <=0 are true. Ignoring correlations between distinct linear forms is
an overapproximation: Boolean UNSAT proves impossibility, SAT is not a concrete
marking or witness. Optional semantic binary clauses require exact arithmetic
proofs of validity over all nonnegative markings, or explicit references to
separately checked global invariants. Initial truths are not semantic axioms.

Encode a target equality a.m=b as P(a,b) AND NOT P(a,b+1). Every original target
row is represented; this removes the positive-place-necessity limitation but
is still incomplete.

Certificate obligations: the concrete initial marking satisfies its invariant;
for every original transition, source mode and destination clause c, prove
`I_source AND Enabled_t AND NOT pullback(c,t)` UNSAT; in every mode prove
`I_mode AND Target` UNSAT. Every formula is 2-CNF. Certificates may provide
paths l -> not-l and not-l -> l. Each edge must reconstruct a named retained
clause, guard/target/pullback unit, threshold-order fact, or checked arithmetic
axiom. Enumerate every obligation; discovery relevance never licenses omission.
Simultaneous induction permits mutually supporting clauses. An unchanged clause
is self-preserving within one mode, but cross-mode transfer requires the source
clause. Pruning must retain all transitive proof dependencies.

Bounded discovery: seed target thresholds and relevant coordinate/initial/arc
constants. Grow candidates by negating unary/binary subsets of failed target
or transition violation cubes. For each finite pool, start with all initially
true candidates and eliminate clauses whose induction formulas are SAT in the
Boolean relaxation until fixed point. On pool growth, reconsider every old
candidate: additional supports can make a formerly eliminated clause inductive.
Use deterministic ordering and explicit thresholds/candidates/round/time caps.
First implement full rescanning; only then compare watched proof dependencies
on identical candidate pools. No model labels or outcome labels in discovery.

A numerical example: initial (x,y,z)=(2,0,0), moves x->y, y->x, 2x->2y and an
unbounded source ->z. With Xk=[x>=k], Yk=[y>=k], the invariant
`NOT X3 AND (NOT X2 OR NOT Y1) AND (NOT X1 OR NOT Y2) AND NOT Y3`
excludes x>=2 AND y>=1. Lower clauses `(X1 OR Y2) AND (X2 OR Y1)` exclude x=y=0.
Reviewer implemented a checker for supplied invariants, not discovery; reports
three examples with 20/10/5 induction obligations, 500 exhaustive truth-table
checks of SCC and 6,964 pullback evaluations. These are not competitive results.

Costs: one graph is O(A+K+r), for A atoms, K clauses, r guards (excluding extra
semantic facts). One SCC check is linear after arithmetic; a sweep can require
T*K checks and naive elimination up to K sweeps. Dependency caching improves
observed work, not worst-case complexity. Clauses may become quadratic; dense
targets, threshold chains, missing affine/modular correlations, higher-arity
invariants, history and certificate size can defeat this approach.

## Proposed experiment and failure criteria

Separate representability, automatic discovery and competitive value. Repair
schema/composition tests first. Differentially check guards, reads, signed and
zero/equality targets, initial states, monitors and mutated paths. Supplied or
compiled phase-pair proofs count as compatibility tests, not discovered coverage.

Retain all 656 slots/640 imports/16 unavailable and duplicates, failed imports,
timeouts and errors. Precompute structural strata by weights, supported safety
proof, independently known boundedness, targets and incidence size. Unsupported
safety is not unboundedness; unit arcs are not safety.

Ablations: binary clauses versus unary; watched dependencies versus full-rescan
with identical candidate pools; one mode versus two on common eligible cases.
Numerical gains must actually use thresholds above one or signed facts, rather
than incidental weight-two arcs. Keep existing presence-only pair results.

Five-second primary budget, matched single-core hardware and resources, separate
independent checking, frozen order and caps. Predeclare a longer-budget fixed
cohort because TokenRing40 required >5s. Report counters as logical work, not
hardware instructions. Repeat balanced runs before claiming stable speedups.
Use strongest frozen native, matched batched, VerifyPN and full portable SMPT.
Only integrate after standalone complementary value; replace a fixed-budget
negative slot under matched scheduling instead of extending total time.

Suggested investment threshold: ten additional independently checked negative
properties across three families, including numerical/signed ablation gains,
plus sparse evaluation/representation and checker-cost benefit. This is a
suggested engineering threshold, not a statistical law. Falsify if benefits
stay within selected TokenRing cases, weighted gains only use Boolean facts,
supplied invariants cannot be discovered, apparent savings lose precision,
missing arithmetic correlations dominate, or validation erases coverage.
Do not rescue a failed hypothesis by adding more expressiveness without a new
experiment. Keep all 22 reserved families untouched until decisions freeze.
