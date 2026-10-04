# Full raw portfolio qualification

All 28 registered rows completed and passed artifact reconciliation. The revised
portfolio independently checks all 27 available exports: 14 reachable and 13
unreachable source slots. One unavailable six-site pairlocked export remains in
the denominator. Four bridge duplicates leave 24 unique source programs, of which
23 have available, independently checked queries. No verdict disagreements.

The diverse cohort checks 12/12; the scaling cohort checks 15/16 slots (15/15
available). This supersedes the remaining-unknown classification for this raw
cohort at these limits without changing historical results. The cohort is now a
regression/scaling baseline, not evidence of unresolved search hardness.

Limits: one local invocation per slot, 60-second input/check-inclusive outer
budget, sampled 2 GiB process-tree RSS, frozen balanced binary and sparse checker.
The solver receives 80% of remaining time. Work allowances are per stage, not an
aggregate instruction budget. No competitive timing or repeated-run stability
claim follows. Source expectations are not the basis for accepting verdicts.

Evidence: `raw-balanced-cohorts-v1-plan.json`,
`raw-balanced-cohorts-v1-verification.json`, and the two complete result folders.
Execution session 15525 returned exit 0. The earlier matched pilot isolated the
scheduling change; this full-cohort run checks coverage only.

Read-only review identified a reusable-runner limitation: direct equality with
saved worker results rejects legitimate conservative outer-limit overrides.
No such override was encountered in this completed run. Future runs should
reconcile through the frozen harness classification function. Preserve the
registered script bytes rather than silently changing this experiment.
