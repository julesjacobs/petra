# Assessment of the completed Pro consultation

2026-09-27. Full answer: `pro-publication-answer.md`; rendered mathematical markup: `pro-publication-answer.html`. Source: https://chatgpt.com/c/6ab917b7-99a8-83ea-8cb3-13a53675ff43. The monitor was stopped after retrieval. The consultation did not inspect the full source or reproduce benchmarks.

## Proposed direction

Pro proposes a single control-indexed token-flow relaxation. For each abstract edge, use its firing count and the sum of source markings at its occurrences. Control-flow and token-moment balance telescope along every concrete execution. Box guards produce independent per-place capacitated flow subproblems after fixing counts and endpoint. Failed flows yield subset cuts in the shared master variables. The proposed raw SER extension proves completed-response membership in a supplied semilinear union using nonnegative integer generator witnesses, avoiding complement construction at that interface.

This is a research proposal. No token-moment or max-flow engine exists in this checkout yet. Pro's claimed small algebra probes were not independently reproduced here. Citations and formulation-level novelty still need independent investigation.

## Assessment against the current artifact

The sparse exact-certificate infrastructure (`linear.rs`) can serve as a master proof layer. The new causal support tree (`causal.rs`) already supplies one checked refinement of execution counts; its correctness does not rely on Pro's answer. Existing `interval.rs` and `projection.rs` are useful references, but their discovery budget and control abstraction need substantial work for this proposal. Projected stuttering transitions must remain in the token-moment model whenever they affect tracked data counters.

The earlier performance summary supplied to Pro is historical. Since then a new family-separated 512-property corpus has been imported and independently checked; 256 evaluation properties remain untouched. Sparse arithmetic alone proved 155/256 development negatives, including 45 old-v2 unknowns. These are independently checked measured results. The corrected portable SMPT configuration and the new combined portfolio still need full measurements. Missing qsolve and public-Tina incompatibility invalidate interpreting the old nominal full-SMPT runs as a fully functioning baseline. VerifyPN is pinned but not yet built.

The key soundness boundary is that each real execution must induce a feasible relaxation point for its terminal control cell. A negative answer requires all possible terminal cells covered. Infinite-domain edges with zero count can carry spurious token moments in the ungated relaxation: retaining them weakens precision but is sound; replacing infinite capacity by an arbitrary finite marking bound can be unsound. Flow feasibility cannot justify reachability; replay remains mandatory.

The next implementation gate should compare a fixed-control full token-moment LP against a per-place flow separator on generated concrete traces and adversarial cases, then test new proof power on all development families and the remaining manual SER example. Do not tune on the sealed evaluation families. Raw SER negative reasoning and strong additional external baselines remain essential unfinished requirements.
