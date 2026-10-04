# VerifyPN-only gap investigation

Investigated the two competitor-only properties from the audited Linux screen.
VerifyPN reports CloudReconfiguration-PT-311__RC06 unreachable and
RefineWMG-PT-100101__RC11 reachable. Native methods timed out on both. These external
results remain tool-reported; this investigation does not assume they are proofs.

A frozen local diagnostic ran portfolio-walk and sparse-count-plan on every
canonical branch: two CloudReconfiguration branches and six RefineWMG branches,
two seconds per branch. This deliberately differs from the original whole-property
budget and is not a competitive timing comparison. Both remain unknown. Cloud's
count planner generates many models and support refinements. RefineWMG generates
no integer model on any branch.

## Verified RefineWMG count-cap obstruction

The sparse planner fixes sum of firing counts <=8192. For RefineWMG branch4, the
native sparse Farkas routine produced a certificate refuting this bounded state
equation. An independent Python checker rebuilt every row directly from original
Petri arcs and target constraints, checked nonnegative rational multipliers and
the final contradiction exactly. The certificate establishes the necessary bound
sum(counts) >=99283/10, hence at least9929 integer firings. It uses target rows0and1;
this statement is about branch4, not a claimed lower bound for all branches.

Added solve_sparse_with_cap and a diagnostic example; existing solve_sparse and
all previous dense-to-sparse fallbacks retain8192. A fixed-cap regression checks
that exhausted/invalid caps remain unknown and a sufficient cap gives a replayable
witness. Existing count-plan tests pass. Initial compilation found five callers
needing the new private argument; the failed log was preserved and all callers
were corrected without changing their old cap.

Registered targeted branch4 ablation, five-second internal budget,5.3-second outer
limit, sampled2GiB, bounded independent checker:

| Count cap | Result | Checked witness length |
|---|---|---:|
|8192|Unknown; no integer model|—|
|16384|Reachable|9970|
|65536|Reachable|9970|

Both witnesses pass the existing independent Python backend checker. The saved
artifact/source audit passes. This supplies a checked witness for a branch of the
VerifyPN-only positive property. It is not yet a whole-property solver improvement,
new default, whole-cohort result, or stable timing claim.

## Next action

Avoid selecting16384 merely because it solves this case. Test a general policy
that derives the firing-count cap from the remaining expanded-trace search budget:
the current realizer consumes a search state per firing, while its allowed state
budget is much larger than8192. Compare that policy against8192 and frozen strong
controls on the complete development corpus, including negatives. If compressed
realization is later introduced, revisit the relationship between firing counts
and state budget. Cloud's negative gap needs a separate support/refutation analysis.

Evidence: plan.json/runs.jsonl/terminal.json; count-bound-8192.json and independent
count-bound-check.json; cap-plan.json/cap-results.json/cap-audit.json; all build,
test and checker logs. The independent cap certificate is not a reachability
unreachability certificate. No main portfolio behavior has changed.
