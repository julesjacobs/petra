# Automatic signed-threshold discovery v1

Opt-in CLI methods `signed-threshold` and `signed-threshold-unary` use the same
exact supplied-invariant kernel, respectively allowing clauses of arity2or1.
The default portfolio and its positive-search schedule are unchanged.

The initial failure cube is the complete target conjunction: inequalities are
positive threshold literals, equalities additionally contribute negated b+1.
Negate every unary/binary subset and keep initially true, non-tautological,
deduplicated clauses. Forms originate in target rows or coordinate guards;
no model names, metadata safety assumptions or synthesized affine directions.

For each fixed pool, assume all eligible clauses and repeatedly remove any
clause whose induction obligation is Boolean-satisfiable for an original
transition. Every pass uses the same current retained set (simultaneous
elimination), until fixed point. Unchanged clauses are self-preserved in this
single-mode invariant. Original weighted guards and exact pullbacks are retained
for all affected transition obligations. Sparse incidence identifies updates;
this is an exact zero-change test, not trusted relevance pruning.

If retained clauses exclude the target, emit a certificate only after the full
Rust verifier rechecks the original problem. Otherwise grow the pool from the
recorded failed transition cubes and restart from the full eligible pool.
Previously removed clauses may be revived by new supporting clauses. Failure to
grow, exhaustion or unsupported proof returns Unknown. There is no positive
answer path in this engine; abstract valuations are never concrete witnesses.

Fixed caps:2048candidate clauses,64candidate forms,64thresholds per candidate
form,8checked pool rounds (at most7expansions). Guard-only temporary forms do not consume the candidate
vocabulary cap. Proposal order, clause order and transition order are
deterministic. `--max-states` supplies the logical discovery allowance (2million
in the registered full screen). Charges cover proposals, clauses/literals,
form terms and incidence work; these are not CPU instructions or runtime bounds.
Final certificate checking and serialization share the wall deadline but have no
separate logical-work charge. Outside resource enforcement remains necessary.

The kernel's guard construction is now lazy and form updates use sparse
incidence, avoiding a transition-by-all-guard-form table. The independent Python
checker remains unchanged. Initial proofs are full retained clause sets, with
no proof-path compression, watched dependency cache, trace monitor, or
cross-form arithmetic axioms.

Correctness gates include automatic upper/lower binary discovery on a weighted
net with an unrelated unbounded source; unary loses the relational proof;
reachable targets and invariant-breaking transitions are not refuted;336small
conservative-net queries compare produced certificates against exhaustive
reachability and both checkers. Supplied-kernel differential and malformed-input
regressions remain required. Caps and deadline/work exhaustion cannot emit proof.

First corpus screen (prepared before execution): all656ordinary development
slots,640imports/16unavailable, binary versus unary,1312rows, one local repeat,
5s original PNML/XML solve, sampled2GiB, separate60s/2GiB independent translation
and proof checking. Frozen binary/source/isolated runner; duplicates and all
failures retained. This measures standalone capability, not portfolio integration,
Linux speedups or general superiority.22reserved families excluded. User's
priority is automatic coverage and speed; checking supports correctness.
