# Second coverage diagnostic

Artifact audit passes: 93 rows, all 31 survivors, exact frozen binary/source/input pins, terminal hashes and bounded independent original-input validation. All 25 definitive answers passed their saved independent checks.

| Method | Solved /31 | Exclusive among these methods | Unknown |
|---|---:|---:|---:|
| backward-cover | 0 | 0 | 31 |
| scaled-relaxed | 12 | 6 | 19 |
| portfolio-excess | 13 | 7 | 18 |

The union solves 19/31; 12 remain unresolved. The union combines separate five-second invocations and is not a measured five-second portfolio.

Each invocation used the same frozen binary and original PNML/XML with a strict five-second whole-property deadline. Only `portfolio-excess` used buffer agglomeration. Validation ran separately with a 60-second limit and sampled 2 GiB. All 31 original slots and all unsuccessful outcomes remain in the denominator.

## Checked successes and costs

| Query | Method | Verdict | Solver seconds | Validator seconds | Parse seconds | Solve seconds |
|---|---|---|---:|---:|---:|---:|
| RERS17pb114-PT-5__RC00 | portfolio-excess | reachable | 0.905 | 5.753 | 0.603 | 0.253 |
| RERS17pb114-PT-5__RC00 | scaled-relaxed | reachable | 4.214 | 3.922 | 0.706 | 3.442 |
| RERS17pb114-PT-5__RC01 | portfolio-excess | reachable | 0.816 | 3.366 | 0.431 | 0.334 |
| RERS17pb114-PT-5__RC01 | scaled-relaxed | reachable | 0.835 | 3.498 | 0.442 | 0.363 |
| RERS17pb114-PT-5__RC03 | portfolio-excess | reachable | 0.940 | 3.451 | 0.428 | 0.444 |
| RERS17pb114-PT-5__RC03 | scaled-relaxed | reachable | 1.432 | 3.306 | 0.468 | 0.919 |
| RERS17pb114-PT-5__RC05 | portfolio-excess | reachable | 1.024 | 3.480 | 0.439 | 0.537 |
| RERS17pb114-PT-5__RC06 | portfolio-excess | reachable | 3.030 | 3.411 | 0.523 | 2.465 |
| RERS17pb114-PT-5__RC07 | portfolio-excess | reachable | 0.659 | 3.491 | 0.421 | 0.201 |
| RERS17pb114-PT-5__RC08 | scaled-relaxed | reachable | 1.346 | 3.396 | 0.455 | 0.851 |
| RERS17pb114-PT-5__RC10 | scaled-relaxed | reachable | 3.582 | 3.357 | 0.587 | 2.956 |
| RERS17pb114-PT-5__RC13 | portfolio-excess | reachable | 0.686 | 3.642 | 0.450 | 0.193 |
| RERS17pb114-PT-5__RC15 | scaled-relaxed | reachable | 1.489 | 3.258 | 0.468 | 0.953 |
| RERS17pb114-PT-9__RC02 | scaled-relaxed | reachable | 1.459 | 3.344 | 0.492 | 0.922 |
| RERS17pb114-PT-9__RC03 | portfolio-excess | reachable | 0.675 | 3.426 | 0.472 | 0.178 |
| RERS17pb114-PT-9__RC03 | scaled-relaxed | reachable | 1.289 | 3.313 | 0.487 | 0.742 |
| RERS17pb114-PT-9__RC05 | portfolio-excess | reachable | 0.980 | 3.818 | 0.599 | 0.312 |
| RERS17pb114-PT-9__RC06 | portfolio-excess | reachable | 1.022 | 3.456 | 0.480 | 0.488 |
| RERS17pb114-PT-9__RC09 | scaled-relaxed | reachable | 1.585 | 3.311 | 0.504 | 1.025 |
| RERS17pb114-PT-9__RC12 | portfolio-excess | reachable | 0.581 | 3.527 | 0.416 | 0.140 |
| RERS17pb114-PT-9__RC12 | scaled-relaxed | reachable | 1.181 | 3.494 | 0.461 | 0.667 |
| RERS17pb114-PT-9__RC13 | scaled-relaxed | reachable | 4.363 | 3.735 | 0.515 | 3.806 |
| RERS17pb114-PT-9__RC14 | portfolio-excess | reachable | 3.949 | 3.463 | 0.442 | 3.461 |
| RERS17pb114-PT-9__RC14 | scaled-relaxed | reachable | 4.352 | 3.455 | 0.455 | 3.858 |
| RERS17pb114-PT-9__RC15 | portfolio-excess | reachable | 0.707 | 3.581 | 0.468 | 0.195 |

## Scheduling evidence

Scaled-relaxed solves 6 properties missed by this portfolio:

- `RERS17pb114-PT-5__RC08`
- `RERS17pb114-PT-5__RC10`
- `RERS17pb114-PT-5__RC15`
- `RERS17pb114-PT-9__RC02`
- `RERS17pb114-PT-9__RC09`
- `RERS17pb114-PT-9__RC13`

Compared descriptively with the earlier direct `walk-guided` screen, scaled-relaxed adds 6 properties. The earlier binary differs, so this is development guidance rather than an isolated ablation.

- `RERS17pb114-PT-5__RC08`
- `RERS17pb114-PT-5__RC10`
- `RERS17pb114-PT-5__RC15`
- `RERS17pb114-PT-9__RC02`
- `RERS17pb114-PT-9__RC09`
- `RERS17pb114-PT-9__RC13`

The earlier direct walk has 1 additional solved queries:

- `ASLink-PT-05b__RC05`

## Failures and deadlines

| Method | Failure flags | Complete JSON /31 | Empty/incomplete JSON | Late definitive JSON |
|---|---|---:|---:|---:|
| backward-cover | nonzero_exit: 4, timeout: 15 | 27 | 4 | 0 |
| scaled-relaxed | none | 31 | 0 | 0 |
| portfolio-excess | nonzero_exit: 7, timeout: 16 | 24 | 7 | 0 |

Saved-output completeness does not reveal unpublished search progress. Failed or late runs remain unknown. The full query sets and timings are in `audit.json`. This selected diagnostic does not establish overall coverage or stable speed; integrated scheduling must be measured on the complete 368-property cohort.
