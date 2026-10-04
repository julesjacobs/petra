# Firing-count cap from remaining trace-search budget

Added solve_sparse_with_state_budget and experimental CLI method
sparse-count-plan-budget. Default solve_sparse and all existing portfolio/fallback
calls retain the fixed8192cap. Both policies share the same arithmetic and trace
realization code, so this experiment isolates count-cap selection.

Before each integer-model query, the new policy bounds total firing counts by
max_states minus states already spent minus one, clamped to the arithmetic
backend's i32::MAX. The reserved state reflects the realizer's existing behavior:
it checks the limit before accepting its final marking. This is a bound for the
current expanded-trace realizer, not for a future compressed executor. No budget
failure becomes an unreachability claim.

Existing count-plan tests and three cap tests pass, including the acceptance
boundary, empty execution and a9000-firing witness beyond the old cap. Targeted
Clippy, release example and CLI build pass. Original defaults remain unchanged.

The diagnosed RefineWMG branch4 is still unknown with the fixedcap and reachable
with the new policy, with an independently checked9970-firing trace. More
importantly, both methods were run against the full original PNML/XML property
RefineWMG-PT-100101__RC11 at five seconds and with buffer agglomeration. Fixedcap
remains unknown across all six branches; the new method solves branch0 with a
29381-firing witness. The bounded original-input validator independently
translates the PNML/XML, checks canonical branch agreement and replays the witness.
This is a checked end-to-end development result, not a speed comparison with the
Linux competitors or a general performance claim.

A separate frozen192-property comparison is running as count-budget-development-v1:
fixed-count planner, budget-count planner, frozen SMTcycles and two frozen native
controls;960rows,one-second whole-property budgets across canonical branches,
sampled2GiB and separate independent checking. Ten capability cases pass. Candidate
example plus experimental CLI binary and full source are preserved under
results/solver-count-budget-development-v1. No whole-cohort result yet.

The earlier targeted cap-probe source was preserved against its recorded hashes;
count_plan.rs was reconstructed by reversing the subsequent policy edit and its
SHA256 verified identical. The snapshot mapping is recorded separately without
altering the old plan or results. This source preservation is post-run, not a claim
that those files were archived before execution.
