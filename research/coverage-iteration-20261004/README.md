# First coverage diagnostic after grouped excess

Selected all 31 unknown properties from the frozen 337/368 grouped-excess screen. Each received two separate five-second original-input invocations, backward-cover and an updated portfolio-excess, with independent original-input checking outside timing. This is a diagnostic, not a full-cohort comparison.

All 62 scheduled rows completed. Backward cover solved none. The updated portfolio solved one: RERS17pb114-PT-5 RC01, by relaxed-batched in 3.156 seconds with a checked 438-transition witness. All remaining outcomes are retained in `results/coverage-diagnostic-20261004`. The plan, source and binary snapshot, terminal artifact hashes and logs are retained here.

The updated source avoids repeated per-transition validation allocations, retains exact enabled actions in relaxed search, realizes acyclic count plans in topological blocks, checks the initial marking earlier, and skips the causal arithmetic precheck when its estimated construction exceeds 100,000 work units. Profiling showed that the prior causal construction consumed the deadline on large RERS nets, preventing later search from running. The relaxed search still expanded relatively few states; subsequent diagnostics give each direct search a full budget.

Backward cover builds an antichain for an upward-closed necessary target and exports a predecessor-closed basis for negative answers. It remains standalone because this diagnostic found no coverage benefit. Later repeated-preimage changes are absent from this frozen binary and have their own diagnostic.

The `full-tests.log` records an intermediate failed test caused by an overly restrictive precheck estimate tied to max_states. The corrected constant estimate passes the complete suite in `full-tests-v2.log`. No failed experiment or log was replaced.
