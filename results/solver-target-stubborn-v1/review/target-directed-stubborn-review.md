# Target-directed stubborn sets

Status: proposal independently reviewed by two agents and the coordinator;
not implemented or benchmarked. Applies to ordinary weighted P/T nets with a
conjunctive signed linear target and mathematical natural-number markings.

At a non-target marking m, choose one false constraint. Seed every transition,
including disabled transitions, whose exact incidence effect has the required
sign: positive below its bound, negative above an equality bound. Close the set
S at m. An enabled member includes symmetric disabling dependencies: all net
consumers of its guard places, and all readers of places it net-consumes. A
disabled member chooses one deficient guard place and includes every positive
net producer of that place. Expand all enabled members of the completed S.

Every target-reaching trace contains a seed, since its total change in the
selected linear form must have the required strict sign. Consider the first S
transition t on a shortest trace of length d. If t were disabled at m, all net
producers of its selected deficient place would belong to S. The preceding
outside-S transitions could not increase that place, contradicting executability
of t. Thus t is enabled at m. Symmetric dependencies allow t to commute before
the outside-S prefix while preserving all guards and the final marking. Its
successor has shortest target distance exactly d-1.

This gives progress without target invisibility, freshness, or periodic full
expansion. Marking-only deduplication is sufficient, provided expansion is fair.
Empty seeds or no enabled closure member imply local unreachability only after
complete, exact construction. Existing witness-only search should continue to
return Unknown on exhaustion until it can produce a checked negative certificate.

Implementation obligations:

- Never reuse saturating `Action.effects` or heuristic target evaluation for
  proof-relevant signs. Use arbitrary precision or checked arithmetic with full
  expansion/Unknown on failure.
- Include every improving alternative and disabled improving transition. Expand
  every enabled closure member, even if absent from the helpful-action list.
- Incomplete closure, resource exhaustion, or arithmetic failure must never
  produce a partial reduction.
- Treat token overflow as Unknown, never disabled. Commutation can increase
  intermediate token counts; fixed-width search has no unrestricted mathematical
  completeness guarantee.
- Apply to each conjunctive branch separately. Relevance slicing needs its own
  preservation argument. The existing slice retains target-changing transitions,
  their guards and recursively every positive net producer of those guards.

Adversarial examples: with a=1, u:a->a+r and t:a->g, target r=g=1 requires reader
u in the closure seeded by t. With empty marking, t:empty->g and u:empty->g+h,
target g=h=1 requires both improving seeds; keeping only t loses the solution.
Tests should additionally cover weighted guards, disabled enabling chains,
equality from either side, exact cancellation beyond i128, seen/no-op successors,
and exhaustive bounded comparison of reachability and shortest target distance.

Prior art: vendored VerifyPN `ReachabilityStubbornSet.cpp` evaluates the query,
uses `InterestingTransitionVisitor`, then closes its stubborn set. That visitor
selects a false conjunct and handles increasing/decreasing expressions. Default
VerifyPN has stubborn reduction enabled, and our default competitor runner does
not disable it. This is evidence of related existing machinery, not evidence
that a particular measured answer used that phase. No novelty claim or code
copying follows from this proposal.
