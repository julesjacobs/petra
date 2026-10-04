# Integrated portfolio survivor screen

Artifact audit passes: 31 rows, all 31 survivors, exact frozen binary/source/input pins, terminal hashes and bounded independent original-input validation. All 26 definitive answers passed their saved independent checks.

| Method | Solved /31 | Exclusive among these methods | Unknown |
|---|---:|---:|---:|
| portfolio-excess | 26 | 26 | 5 |

The integrated portfolio solves 26/31; 5 remain unresolved. Each property uses one shared five-second invocation. This selected survivor screen does not establish whole-cohort coverage.

Each invocation used the same frozen binary and original PNML/XML with a strict five-second whole-property deadline. Only `portfolio-excess` used buffer agglomeration. Validation ran separately with a 60-second limit and sampled 2 GiB. All 31 original slots and all unsuccessful outcomes remain in the denominator.

## Checked successes and costs

| Query | Method | Verdict | Solver seconds | Validator seconds | Parse seconds | Solve seconds |
|---|---|---|---:|---:|---:|---:|
| ASLink-PT-05b__RC05 | portfolio-excess | reachable | 0.153 | 0.128 | 0.007 | 0.111 |
| RERS17pb114-PT-5__RC00 | portfolio-excess | reachable | 0.578 | 3.374 | 0.442 | 0.100 |
| RERS17pb114-PT-5__RC01 | portfolio-excess | reachable | 0.549 | 3.505 | 0.435 | 0.067 |
| RERS17pb114-PT-5__RC03 | portfolio-excess | reachable | 0.908 | 3.332 | 0.431 | 0.419 |
| RERS17pb114-PT-5__RC04 | portfolio-excess | reachable | 0.573 | 3.356 | 0.431 | 0.087 |
| RERS17pb114-PT-5__RC05 | portfolio-excess | reachable | 1.553 | 3.515 | 0.431 | 1.068 |
| RERS17pb114-PT-5__RC06 | portfolio-excess | reachable | 0.635 | 3.302 | 0.456 | 0.144 |
| RERS17pb114-PT-5__RC07 | portfolio-excess | reachable | 0.598 | 3.358 | 0.429 | 0.120 |
| RERS17pb114-PT-5__RC08 | portfolio-excess | reachable | 0.576 | 3.492 | 0.446 | 0.088 |
| RERS17pb114-PT-5__RC10 | portfolio-excess | reachable | 0.621 | 3.298 | 0.434 | 0.140 |
| RERS17pb114-PT-5__RC11 | portfolio-excess | reachable | 0.552 | 3.871 | 0.427 | 0.086 |
| RERS17pb114-PT-5__RC13 | portfolio-excess | reachable | 1.238 | 3.496 | 0.409 | 0.774 |
| RERS17pb114-PT-5__RC14 | portfolio-excess | reachable | 0.968 | 3.507 | 0.412 | 0.151 |
| RERS17pb114-PT-5__RC15 | portfolio-excess | reachable | 0.567 | 3.322 | 0.454 | 0.074 |
| RERS17pb114-PT-9__RC00 | portfolio-excess | reachable | 1.357 | 3.328 | 0.475 | 0.839 |
| RERS17pb114-PT-9__RC02 | portfolio-excess | reachable | 0.694 | 3.584 | 0.435 | 0.229 |
| RERS17pb114-PT-9__RC03 | portfolio-excess | reachable | 0.539 | 3.473 | 0.436 | 0.068 |
| RERS17pb114-PT-9__RC05 | portfolio-excess | reachable | 0.824 | 3.536 | 0.447 | 0.325 |
| RERS17pb114-PT-9__RC06 | portfolio-excess | reachable | 0.887 | 3.487 | 0.420 | 0.413 |
| RERS17pb114-PT-9__RC08 | portfolio-excess | reachable | 0.575 | 3.275 | 0.423 | 0.115 |
| RERS17pb114-PT-9__RC09 | portfolio-excess | reachable | 0.746 | 3.336 | 0.510 | 0.176 |
| RERS17pb114-PT-9__RC11 | portfolio-excess | reachable | 1.043 | 3.748 | 0.426 | 0.571 |
| RERS17pb114-PT-9__RC12 | portfolio-excess | reachable | 0.599 | 3.769 | 0.474 | 0.087 |
| RERS17pb114-PT-9__RC13 | portfolio-excess | reachable | 0.605 | 3.524 | 0.455 | 0.103 |
| RERS17pb114-PT-9__RC14 | portfolio-excess | reachable | 0.642 | 3.519 | 0.513 | 0.090 |
| RERS17pb114-PT-9__RC15 | portfolio-excess | reachable | 0.616 | 3.477 | 0.459 | 0.113 |

## Failures and deadlines

| Method | Failure flags | Complete JSON /31 | Empty/incomplete JSON | Late definitive JSON |
|---|---|---:|---:|---:|
| portfolio-excess | nonzero_exit: 1, timeout: 4 | 30 | 1 | 0 |

Saved-output completeness does not reveal unpublished search progress. Failed or late runs remain unknown. The full query sets and timings are in `audit.json`. This selected diagnostic does not establish overall coverage or stable speed; integrated scheduling must be measured on the complete 368-property cohort.
