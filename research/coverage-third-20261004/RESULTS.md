# Third coverage diagnostic

Artifact audit passes: 93 rows, all 31 survivors, exact frozen binary/source/input pins, terminal hashes and bounded independent original-input validation. All 54 definitive answers passed their saved independent checks.

| Method | Solved /31 | Exclusive among these methods | Unknown |
|---|---:|---:|---:|
| walk-guided | 14 | 1 | 17 |
| scaled-walk | 25 | 8 | 6 |
| portfolio-excess | 15 | 0 | 16 |

The union solves 26/31; 5 remain unresolved. The union combines separate five-second invocations and is not a measured five-second portfolio.

Each invocation used the same frozen binary and original PNML/XML with a strict five-second whole-property deadline. Only `portfolio-excess` used buffer agglomeration. Validation ran separately with a 60-second limit and sampled 2 GiB. All 31 original slots and all unsuccessful outcomes remain in the denominator.

## Checked successes and costs

| Query | Method | Verdict | Solver seconds | Validator seconds | Parse seconds | Solve seconds |
|---|---|---|---:|---:|---:|---:|
| ASLink-PT-05b__RC05 | walk-guided | reachable | 0.130 | 0.142 | 0.007 | 0.086 |
| RERS17pb114-PT-5__RC00 | portfolio-excess | reachable | 0.661 | 3.286 | 0.439 | 0.196 |
| RERS17pb114-PT-5__RC00 | scaled-walk | reachable | 0.612 | 3.285 | 0.461 | 0.094 |
| RERS17pb114-PT-5__RC00 | walk-guided | reachable | 0.590 | 3.344 | 0.455 | 0.088 |
| RERS17pb114-PT-5__RC01 | portfolio-excess | reachable | 0.762 | 3.370 | 0.427 | 0.308 |
| RERS17pb114-PT-5__RC01 | scaled-walk | reachable | 0.576 | 3.311 | 0.463 | 0.060 |
| RERS17pb114-PT-5__RC01 | walk-guided | reachable | 0.730 | 3.374 | 0.481 | 0.201 |
| RERS17pb114-PT-5__RC03 | portfolio-excess | reachable | 0.898 | 3.382 | 0.437 | 0.416 |
| RERS17pb114-PT-5__RC03 | scaled-walk | reachable | 1.052 | 3.331 | 0.508 | 0.420 |
| RERS17pb114-PT-5__RC03 | walk-guided | reachable | 0.868 | 3.372 | 0.512 | 0.298 |
| RERS17pb114-PT-5__RC04 | scaled-walk | reachable | 0.723 | 3.898 | 0.584 | 0.088 |
| RERS17pb114-PT-5__RC05 | portfolio-excess | reachable | 0.984 | 3.585 | 0.451 | 0.489 |
| RERS17pb114-PT-5__RC05 | scaled-walk | reachable | 2.746 | 3.604 | 0.466 | 2.234 |
| RERS17pb114-PT-5__RC05 | walk-guided | reachable | 0.902 | 3.583 | 0.461 | 0.385 |
| RERS17pb114-PT-5__RC06 | scaled-walk | reachable | 0.749 | 3.264 | 0.535 | 0.159 |
| RERS17pb114-PT-5__RC06 | walk-guided | reachable | 2.518 | 3.470 | 0.488 | 1.963 |
| RERS17pb114-PT-5__RC07 | portfolio-excess | reachable | 0.756 | 3.784 | 0.495 | 0.215 |
| RERS17pb114-PT-5__RC07 | scaled-walk | reachable | 0.698 | 3.465 | 0.530 | 0.120 |
| RERS17pb114-PT-5__RC07 | walk-guided | reachable | 0.651 | 3.414 | 0.513 | 0.093 |
| RERS17pb114-PT-5__RC08 | portfolio-excess | reachable | 3.279 | 3.431 | 0.504 | 2.714 |
| RERS17pb114-PT-5__RC08 | scaled-walk | reachable | 0.580 | 3.338 | 0.458 | 0.083 |
| RERS17pb114-PT-5__RC10 | scaled-walk | reachable | 0.695 | 3.298 | 0.502 | 0.149 |
| RERS17pb114-PT-5__RC11 | scaled-walk | reachable | 0.606 | 3.966 | 0.477 | 0.079 |
| RERS17pb114-PT-5__RC13 | portfolio-excess | reachable | 0.675 | 3.779 | 0.450 | 0.186 |
| RERS17pb114-PT-5__RC13 | scaled-walk | reachable | 3.206 | 3.859 | 0.480 | 2.679 |
| RERS17pb114-PT-5__RC13 | walk-guided | reachable | 0.592 | 3.529 | 0.456 | 0.077 |
| RERS17pb114-PT-5__RC14 | scaled-walk | reachable | 0.643 | 3.538 | 0.455 | 0.146 |
| RERS17pb114-PT-5__RC15 | portfolio-excess | reachable | 3.152 | 3.340 | 0.453 | 2.653 |
| RERS17pb114-PT-5__RC15 | scaled-walk | reachable | 0.600 | 3.338 | 0.482 | 0.068 |
| RERS17pb114-PT-9__RC00 | scaled-walk | reachable | 1.414 | 3.339 | 0.517 | 0.852 |
| RERS17pb114-PT-9__RC02 | portfolio-excess | reachable | 3.277 | 3.523 | 0.452 | 2.753 |
| RERS17pb114-PT-9__RC02 | scaled-walk | reachable | 0.773 | 3.388 | 0.498 | 0.232 |
| RERS17pb114-PT-9__RC03 | portfolio-excess | reachable | 0.681 | 3.305 | 0.468 | 0.167 |
| RERS17pb114-PT-9__RC03 | scaled-walk | reachable | 0.581 | 3.322 | 0.458 | 0.071 |
| RERS17pb114-PT-9__RC03 | walk-guided | reachable | 0.592 | 3.337 | 0.469 | 0.070 |
| RERS17pb114-PT-9__RC05 | portfolio-excess | reachable | 0.766 | 3.463 | 0.481 | 0.250 |
| RERS17pb114-PT-9__RC05 | scaled-walk | reachable | 0.805 | 3.454 | 0.449 | 0.318 |
| RERS17pb114-PT-9__RC05 | walk-guided | reachable | 0.734 | 3.770 | 0.539 | 0.129 |
| RERS17pb114-PT-9__RC06 | portfolio-excess | reachable | 0.915 | 3.546 | 0.435 | 0.431 |
| RERS17pb114-PT-9__RC06 | scaled-walk | reachable | 0.905 | 3.600 | 0.469 | 0.403 |
| RERS17pb114-PT-9__RC06 | walk-guided | reachable | 0.867 | 3.670 | 0.485 | 0.326 |
| RERS17pb114-PT-9__RC08 | scaled-walk | reachable | 0.693 | 3.530 | 0.531 | 0.108 |
| RERS17pb114-PT-9__RC09 | portfolio-excess | reachable | 3.258 | 3.382 | 0.430 | 2.797 |
| RERS17pb114-PT-9__RC09 | scaled-walk | reachable | 0.701 | 3.373 | 0.502 | 0.153 |
| RERS17pb114-PT-9__RC11 | scaled-walk | reachable | 1.158 | 3.591 | 0.477 | 0.647 |
| RERS17pb114-PT-9__RC12 | portfolio-excess | reachable | 0.606 | 3.574 | 0.423 | 0.149 |
| RERS17pb114-PT-9__RC12 | scaled-walk | reachable | 0.567 | 3.526 | 0.452 | 0.065 |
| RERS17pb114-PT-9__RC12 | walk-guided | reachable | 0.558 | 3.559 | 0.460 | 0.042 |
| RERS17pb114-PT-9__RC13 | scaled-walk | reachable | 0.708 | 3.902 | 0.538 | 0.136 |
| RERS17pb114-PT-9__RC14 | scaled-walk | reachable | 0.639 | 3.550 | 0.484 | 0.081 |
| RERS17pb114-PT-9__RC14 | walk-guided | reachable | 3.685 | 3.627 | 0.464 | 3.173 |
| RERS17pb114-PT-9__RC15 | portfolio-excess | reachable | 0.708 | 3.550 | 0.467 | 0.198 |
| RERS17pb114-PT-9__RC15 | scaled-walk | reachable | 0.634 | 3.569 | 0.478 | 0.102 |
| RERS17pb114-PT-9__RC15 | walk-guided | reachable | 0.609 | 3.586 | 0.464 | 0.088 |

## Scheduling evidence

Scaled-walk solves 10 properties missed by this portfolio:

- `RERS17pb114-PT-5__RC04`
- `RERS17pb114-PT-5__RC06`
- `RERS17pb114-PT-5__RC10`
- `RERS17pb114-PT-5__RC11`
- `RERS17pb114-PT-5__RC14`
- `RERS17pb114-PT-9__RC00`
- `RERS17pb114-PT-9__RC08`
- `RERS17pb114-PT-9__RC11`
- `RERS17pb114-PT-9__RC13`
- `RERS17pb114-PT-9__RC14`

Compared descriptively with the earlier direct `walk-guided` screen, scaled-walk adds 12 properties. The earlier binary differs, so this is development guidance rather than an isolated ablation.

- `RERS17pb114-PT-5__RC04`
- `RERS17pb114-PT-5__RC08`
- `RERS17pb114-PT-5__RC10`
- `RERS17pb114-PT-5__RC11`
- `RERS17pb114-PT-5__RC14`
- `RERS17pb114-PT-5__RC15`
- `RERS17pb114-PT-9__RC00`
- `RERS17pb114-PT-9__RC02`
- `RERS17pb114-PT-9__RC08`
- `RERS17pb114-PT-9__RC09`
- `RERS17pb114-PT-9__RC11`
- `RERS17pb114-PT-9__RC13`

The earlier direct walk has 3 additional solved queries:

- `RERS17pb114-PT-5__RC06`
- `RERS17pb114-PT-9__RC14`
- `ASLink-PT-05b__RC05`

## Failures and deadlines

| Method | Failure flags | Complete JSON /31 | Empty/incomplete JSON | Late definitive JSON |
|---|---|---:|---:|---:|
| walk-guided | nonzero_exit: 5, timeout: 14 | 27 | 4 | 0 |
| scaled-walk | none | 31 | 0 | 0 |
| portfolio-excess | nonzero_exit: 5, timeout: 14 | 26 | 5 | 0 |

Saved-output completeness does not reveal unpublished search progress. Failed or late runs remain unknown. The full query sets and timings are in `audit.json`. This selected diagnostic does not establish overall coverage or stable speed; integrated scheduling must be measured on the complete 368-property cohort.
