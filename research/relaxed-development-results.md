# First complete relaxed-search comparison

At a five-second original-input deadline, the new portfolio solved 255/256 development properties; revised causal solved 238, unrestricted VerifyPN 251 and trace-enabled VerifyPN 251. All native definitive answers were independently checked, with no definitive disagreements or errors. The recorded run is `results/publication-relaxed-development`; exact gains/losses are in `research/relaxed-development-comparison.json`.

The new search added 17 positives over revised causal with no lost solves. Five positives were unknown in both VerifyPN configurations: CANConstruction020 RC01, CANConstruction040 RC02/RC03, Echo d02r15 RC05/RC08. VerifyPN alone proved the remaining Rust unknown, JoinFreeModules0005 RC09. Thus Rust has higher coverage in this pass, while neither method subsumes the other.

This is one shared-host development run with sampled 2 GiB RSS, cold processes, original PNML/XML inputs and a seeded rotation of method order. It establishes neither a universal speedup nor publication readiness. All 256 held-out evaluation properties remain unused. Retired-instruction measurements on Linux are still incomplete after a runner teardown race, and must not be summarized as a complete comparison.

Source-level review found no soundness blocker in relaxed search. Its heuristic affects expansion order only; every positive has an original-net witness. Current state-cap and tie-order choices remain possible ablations. Delete-relaxed planning and preferred operators are established methods; algorithmic novelty is not established by this result.
