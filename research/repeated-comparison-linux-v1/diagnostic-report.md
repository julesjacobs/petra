# Repeated comparison: conservative diagnostic

The six registered blocks completed with 4,224 rows. Five artifact audits pass; `b2-30s` fails. The frozen summarizer refuses the suite, so no registered complete-audited summary is available.

SMPT reports FALSE for `RefineWMG-PT-100101__RC09` in `b2-30s`, with exit 0 and `subprocess_error=true`. Its log contains `BrokenPipeError` before the formula output. The existing auditor excludes this answer. Native checked answers and VerifyPN agree FALSE, but that agreement does not override the registered failure rule.

These diagnostic tables use the existing auditor accepted-solved classification, retaining the rejected answer as failure and charging it the registered PAR-2 penalty. They do not waive the failed audit. All primary counts use 175 distinct ordered-branch representatives; the JSON also retains all 176 original properties.

## 5-second budget

| Method | Solved by block /175 | Solved in all three /175 | Any repeat /175 | Mean PAR-2 seconds |
|---|---|---:|---:|---:|
| native-reduced | 135, 135, 134 | 134 | 135 | 2.548191 |
| native-frozen | 128, 128, 128 | 128 | 128 | 2.767597 |
| verifypn-default | 129, 129, 129 | 129 | 129 | 2.801487 |
| smpt-mcc-portable | 94, 95, 96 | 88 | 101 | 5.477263 |

Block order: b1-5s, b4-5s, b5-5s.

| Baseline | Candidate gains/losses by block | Gains/losses present in every block |
|---|---|---|
| native-frozen | 7/0, 7/0, 6/0 | 6/0 |
| verifypn-default | 6/0, 6/0, 5/0 | 5/0 |
| smpt-mcc-portable | 41/0, 40/0, 38/0 | 33/0 |

Never solved by any method in any repeat: 40 representatives (DNAwalker: 13, RERS17pb114: 27).

## 30-second budget

| Method | Solved by block /175 | Solved in all three /175 | Any repeat /175 | Mean PAR-2 seconds |
|---|---|---:|---:|---:|
| native-reduced | 143, 143, 143 | 143 | 143 | 11.850984 |
| native-frozen | 138, 137, 138 | 137 | 138 | 13.501047 |
| verifypn-default | 139, 139, 139 | 139 | 139 | 13.258085 |
| smpt-mcc-portable | 116, 119, 121 | 115 | 122 | 21.652627 |

Block order: b2-30s, b3-30s, b6-30s.

| Baseline | Candidate gains/losses by block | Gains/losses present in every block |
|---|---|---|
| native-frozen | 5/0, 6/0, 5/0 | 5/0 |
| verifypn-default | 12/8, 12/8, 12/8 | 12/8 |
| smpt-mcc-portable | 29/2, 26/2, 24/2 | 23/2 |

Never solved by any method in any repeat: 24 representatives (DNAwalker: 5, RERS17pb114: 19).

## Interpretation and limits

The candidate has higher coverage than VerifyPN at both budgets. Its five-second solved set contains VerifyPN’s solved set in every block. At thirty seconds the methods complement each other: the candidate gains 12 representatives and loses 8 in every block. All 8 losses are DNAwalker-PT-09ringLR properties. A five-second superset claim therefore does not extend to thirty seconds.

At thirty seconds the 24 representatives unresolved by every method comprise 5 DNAwalker-PT-18lozangeBlock properties and 19 RERS17pb114 properties. Unresolved describes these budgets and configurations; it does not prove hardness.

Native answers were independently checked during the original runs; the artifact audit verifies saved validation evidence without rerunning proofs. External verdicts remain tool-reported. The cohort informed development, so these results do not establish held-out generalization. Three repeats describe repeatability, not precise population-level uncertainty. CPU affinity is not exclusive host isolation.

PAR-2 charges accepted answers their solver wall time and other outcomes twice the invocation budget. Native validation time is separate. Missing counters are not zero; availability below includes unsuccessful runs and retains all 176 properties × three repeats per method.

| Budget | Method | Counter | Coverage counts /528 |
|---:|---|---|---|
| 5 | native-reduced | instructions:u | full-coverage: 528 |
| 5 | native-reduced | cycles:u | full-coverage: 528 |
| 5 | native-reduced | task-clock | full-coverage: 528 |
| 5 | native-frozen | instructions:u | full-coverage: 528 |
| 5 | native-frozen | cycles:u | full-coverage: 528 |
| 5 | native-frozen | task-clock | full-coverage: 528 |
| 5 | verifypn-default | instructions:u | full-coverage: 528 |
| 5 | verifypn-default | cycles:u | full-coverage: 528 |
| 5 | verifypn-default | task-clock | full-coverage: 528 |
| 5 | smpt-mcc-portable | instructions:u | full-coverage: 525, missing-or-invalid-value: 3 |
| 5 | smpt-mcc-portable | cycles:u | full-coverage: 525, missing-or-invalid-value: 3 |
| 5 | smpt-mcc-portable | task-clock | full-coverage: 525, missing-or-invalid-value: 3 |
| 30 | native-reduced | instructions:u | full-coverage: 516, missing-or-invalid-value: 12 |
| 30 | native-reduced | cycles:u | full-coverage: 516, missing-or-invalid-value: 12 |
| 30 | native-reduced | task-clock | full-coverage: 516, missing-or-invalid-value: 12 |
| 30 | native-frozen | instructions:u | full-coverage: 516, missing-or-invalid-value: 12 |
| 30 | native-frozen | cycles:u | full-coverage: 516, missing-or-invalid-value: 12 |
| 30 | native-frozen | task-clock | full-coverage: 516, missing-or-invalid-value: 12 |
| 30 | verifypn-default | instructions:u | full-coverage: 528 |
| 30 | verifypn-default | cycles:u | full-coverage: 528 |
| 30 | verifypn-default | task-clock | full-coverage: 528 |
| 30 | smpt-mcc-portable | instructions:u | full-coverage: 432, missing-or-invalid-value: 96 |
| 30 | smpt-mcc-portable | cycles:u | full-coverage: 432, missing-or-invalid-value: 96 |
| 30 | smpt-mcc-portable | task-clock | full-coverage: 432, missing-or-invalid-value: 96 |

Exact paired queries, solved frequencies, accepted and observed timing ranges, separate validation time, peak memory, and counter coverage are retained in `diagnostic-summary.json`. `summary.log` preserves the registered summarizer refusal. `b2-30s/audit.json` preserves the failed audit; raw results and all frozen inputs remain unchanged.

Transfer used a read-only remote tar stream at nice 19, idle I/O priority, CPU 9 affinity, and 2 MiB/s; compression and every artifact audit ran locally. No benchmark or build was started.

Suite SHA-256: `8ab24b5b7d3c7fdde01832cbcacd39908764da6ef7df55d10961a4cb9ac94d36`.
