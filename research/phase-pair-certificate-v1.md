# Phase-partitioned pair closure: certificate contract v1

Experimental general safe-net abstraction. No model names or source-language
semantics are trusted. Pair abstraction and trace partitioning are established
techniques; no novelty claim. Prototype ordinary pair closure misses both tested
TokenRing branches; a two-phase prototype closes and excludes branch0of N30.
The N40 prototype reaches its30s limit. Neither is an accepted solver answer yet.

JSON certificate kind `phase-pair-closure-v1`:
- `groups`: arrays of sorted place indices, a disjoint partition of every place.
  Each group has initial token mass at most1 and weighted post mass at most pre mass
  for every original transition. These nonincrease checks prove every place globally
  at most1. Reject missing/duplicate indices, empty groups and invalid arcs.
- `landmarks`: sorted unique original transition indices. Phase0means no such
  transition has fired; phase1means one has fired. Any set is sound.
- `relations`: exactly two matrices; each matrix has n rows, each row is a list
  of ceil(n/64) unsigned64-bit words, little-endian bits within each word.
  Bit j of row i permits simultaneous positive places i,j in that phase.
  Require unused tail bits0, symmetry, and both diagonals for every set pair.
- `conflicts`: exactly two objects with `left` and `right`, each having `place`,
  `constraint` (original target-row index), and `negated` (boolean). A negated
  row is allowed only for equality; it reverses coefficients and bound.

Target certificate: for each phase, the indicated pair must be absent (same
place allowed). Each indicated place must have positive coefficient c in its
signed target row, and sum(max(0,a_j),j!=place) < signed bound. Under the checked
0/1bounds this forces that place to be positive in every target marking.
Use exact integer arithmetic, including when negating i64::MIN. Thus an absent
required pair excludes the target in each phase.

Initial inclusion: phase0must contain all pairs (including diagonals) of
initially marked places. There is no initial obligation on phase1.

Inductive transition closure, for each original transition and each phase:
1. A pre arc of weight>1 is impossible under safety. Also a post arc>1 implies
   this transition cannot be enabled in any reachable safe marking; the checker
   may skip it using the already-verified conservation proof.
2. If any pre-place diagonal or any pre-pair is absent in the source relation,
   the abstract guard is impossible and the obligation is vacuous.
3. Let live be the set of present diagonals in the source. Let compatible be
   live intersected with each pre-place's row. Remove all places in pre\post;
   call the resulting set surviving. This overapproximates old tokens that may
   remain after firing. Read arcs (pre intersect post) are preserved.
4. Destination is1if source is1or transition is a landmark, else0.
5. If destination differs from source, require every source pair among surviving
   places in the destination. This frame obligation is essential: transfer
   pre-existing pairs even when neither is mentioned by the transition.
6. Let produced be all post places. Require produced x (surviving union produced)
   in the destination relation, including diagonals and symmetric pairs.

Every original execution maps to a phase and every occupied pair is included,
by induction and the independent conservation proof. Steps2/3may admit spurious
markings but never discard a reachable successor. Missing proof/deadline/work
limit gives Unknown. A closed relation is a negative certificate only when both
phase target-conflict obligations hold. No positive answer from this abstraction.

Discovery proposal: union places whose counts change together in a transition;
validate resulting components' at-most-one-token nonincrease exactly. Unsupported nets
return Unknown. Choose the component with the fewest count-changing transitions
(stable tie by smallest place index), use those transitions as landmarks. Compute
least pair closure in two phases from original initial pairs; retain uniform
pair closure as an ablation if useful later. All heuristic choices are proposals;
the checker accepts any well-formed partition/landmarks satisfying the contract.
