# ITS-Tools qualification preparation

Status: local acquisition and adapter tests complete; runtime qualification and
performance comparison pending. No ITS performance result is available.

The official MCC wrapper is pinned at
`1b883d1273df87f7523b9c016e7bc1a8733d9b8e`. Its reachability configuration enables
`-its -order META -manyOrder -smt`, with GreatSPN ordering. Preserve this portfolio
as the competitor; omitting `-smt` is a separate ITS-only ablation and does not
establish that preprocessing is SMT-free. Leave LTSmin disabled as upstream does.

The downloaded Linux x86-64 product contains application bundle
`1.0.0.202609112134`, requiring Java 21. Product and GreatSPN archive hashes are in
provenance.json. Neither archive has been executed. The source inspection at
`8a49519f5920de826d34336d736025682545aff1` is newer than the product;
source/binary correspondence is unverified. Do not attribute current source
behavior to this binary without qualification. The optional native image has not
been pinned; the wrapper prefers it when available. JVM startup may materially
affect short budgets, so runtime choice must be explicit before registration.

`scripts/its_adapter.py` stages exactly one requested EF/AG property and copies
PNML bytes unchanged. It records original and staged hashes, refuses duplicate or
missing requested IDs and existing output directories, and preserves the default
XML namespace. Parsing requires an exact property ID and consistent TRUE/FALSE
output from a successful process. Malformed, missing, conflicting, timed-out and
nonzero-exit results remain unknown. AG truth is converted to counterexample
reachability, retaining original property truth. These are external-reported
answers, not independently checked certificates.

Three test methods pass (adapter-tests-v1.log), exercising both polarities,
distractor IDs, conflicts, failed processes, namespace preservation, unchanged
model bytes and isolation of one property. This verifies adapter behavior only.

Before benchmark registration:

1. Resolve runtime packaging, pin all executable dependencies and record source
   correspondence where available. Qualify the exact binary's accepted flags.
2. After the entire existing Linux suite is terminal, run small known-answer
   cases for EF/AG true and false, equality, signed coefficients, read arcs and
   multiple properties. Test unsupported/oversized integer inputs explicitly;
   inspected source parses integer constants as Java int. Failures must not be
   interpreted as mathematical verdicts.
3. Use the original development inputs, one property per invocation, with staging,
   frontend and process startup included in measured time. Apply the same CPU,
   memory and whole-query deadline to the complete process tree. Check whether
   many-order workers compete on the assigned CPU; record the behavior.
4. Preregister full portfolio and ITS-only modes alongside the frozen original
   solver and current combined solver. Keep reserved evaluation families closed.
   Retain raw output, configuration, hashes and all failures. No superiority or
   custom decision-diagram novelty claim follows from this preparation.

The existing six-block Linux comparison remains live: latest observation has
704/704, 704/704, 461/704, 0, 0, 0 rows. No remote deployment, build, collection or
additional measurement was performed.
