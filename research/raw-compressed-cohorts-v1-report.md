# Compressed controls regress the checked n5 proof

All28 registered rows completed and artifact reconciliation passed. Compressed
controls check25/27 available slots:14 reachable and11 unreachable. The prior
dense balanced qualification checked27/27. The regression is one unique program,
`write_skew_n5_pairlocked`, appearing in both cohorts as a retained bridge.

| Cohort | Dense balanced checked | Compressed checked | Compressed remaining |
|---|---:|---:|---|
| Diverse | 12/12 | 11/12 | n5 pairlocked solver timeout |
| Scaling | 15/15 available | 14/15 available | n5 pairlocked solver timeout; n6 pairlocked export unavailable |

All28 source slots,24 unique programs, four bridge duplicates and one unavailable
export remain recorded. Compressed controls check22/23 available unique programs.
All25 definitive rows pass the saved independent check; no verdict disagreement.
The audit used the frozen harness classifier, including conservative outer-limit
overrides, and rechecked all59 artifact hashes. No proof was rerun during audit.

## n5 evidence

| Cohort | Dense result / whole-query wall | Compressed result / whole-query wall | Compressed peak RSS |
|---|---|---|---:|
| Diverse | Checked negative /40.765s | Solver timeout /48.231s | 1405.0 MiB |
| Scaling | Checked negative /42.317s | Solver timeout /48.299s | 1392.9 MiB |

Both compressed worker results say `solver phase deadline`; `solver.stdout` and
`solver.stderr` are empty. The worker exits0 after reporting the timeout; this is
not a successful solver exit. Neither row hits the sampled memory limit or the
60-second outer deadline, and neither reaches independent proof checking. There
is no returned solver work-limit reason or phase trace. Therefore the observed
failure is the approximately48-second solver-phase wall deadline; these artifacts
do not determine whether increased work charges, encoding overhead, discovery,
or portfolio fallback consumed that time. Dense runs emit131,195,414-byte proofs
and independently accept them; their process-tree peaks include checker memory.
Peak RSS is consequently not a matched solver-only memory measurement.

The frozen compressed binary is
`b871e709d8f104f47b7af09f6dcc10da794859b68191c6765ebd945a25f52413`.
The schedule/checker/settings match the prior balanced qualification:60s
input/check-inclusive outer wall,80% of remaining time for the solver, sampled
2GiB RSS,100M states and10B applicable negative/checker work, one local invocation
per source slot. Interning charges changed2d→8d, so this is a candidate regression
comparison, not a pure storage ablation. There is no stable timing or competitor
claim. Keep the compressed candidate experimental; do not replace the baseline
that retains the checked n5 result.

Next, register a bounded n5 phase diagnostic and a matched-charge control-storage
comparison after this experiment closes. Identify the negative stage's stop
reason and whether positive fallback begins, along with graph size and interning
cost. No extra diagnostic, build or solver was launched in this closeout.

Evidence: `raw-compressed-cohorts-v1-plan.json`,
`raw-compressed-cohorts-v1-verification.json`, the two complete result folders,
and the previous `raw-balanced-cohorts-v1-verification.json`. Session75521 exited0;
execution is `complete-audited`.
