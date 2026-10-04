# Direct component invariants: proposed next proof search

This is an unimplemented specialization of `raw-negative-design.md`. It may avoid synthesizing new semilinear pieces or parameter partitions on the locked families. It has not established any negative result.

Keep the verified finite projected controller and nonnegative response-credit map from that design. Restrict each controller state's invariant to a selected union of components from the original serial language. Discover reachable pairs `(controller state, serial component)` by a finite worklist, starting with a component containing the credited initial marking.

For each pair and every enabled projected transition, compute its original credited effect `a`. Find an original serial component `b' + B' N^k` covering the entire shifted source piece `b + a + B N^h`. It suffices to produce nonnegative integer vectors `v` and `H[:,j]` such that:

- `b + a = b' + B' v`;
- `B[:,j] = B' H[:,j]` for every source period.

Add the destination pair to the worklist and retain these coefficient witnesses. If no covering component exists, return unknown. Each mapping proves universal closure because the destination coefficients are `v + H z` for every natural source parameter vector `z`. This is stronger than pointwise membership and retains exact monoid membership, not cone or lattice relaxation.

All invariant pieces are original serial components, so completed-response inclusion is immediate once the credit map is checked to equal actual response counts at completion. Every selected controller transition and source piece must have a checked mapping; stuttering transitions cannot be omitted. The projected controller itself still needs exact finite closure on original arcs.

For the small locked-counter candidate, original finite-prefix components and eventual periodic components appear sufficient: successive credited increments map prefixes to prefixes, then into cycle components. This must be mechanically checked against the actual query. Selecting only original components may fail even when another semilinear invariant would succeed; that is an intended incompleteness.

Remaining discovery questions: choosing a finite controller that excludes unbounded request/wait queues; assigning credits structurally to response-flush places; finding period coefficient witnesses efficiently; and selecting among multiple covering components without an unfortunate choice preventing closure. Candidate choices may need backtracking. No property of program names or lock names belongs in discovery or checking.

Existing exact arithmetic can supply coefficient witnesses: `complete_arithmetic::solve_integer` solves nonnegative integer systems and returns an explicit vector, with deadlines and work limits. Each candidate base/period map must still be independently checked. `raw_target::member` currently returns only a Boolean and loses coefficient indices during period deduplication, so it cannot serve directly as an exported proof witness.

Controller discovery may need the union of several bounded supports rather than one support. For example, one conserved group can encode the global variable state and another the free-lock/inside-critical-section token. Their union has a finite projected state space. Existing `control::discover` finds one one-hot group; enumerating additional groups with different objectives or coverage constraints is a proposal, not implemented evidence. Finite projected closure still needs direct checking from every state and every original transition, regardless of how supports were discovered.
