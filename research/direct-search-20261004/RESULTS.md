# Direct search on the 31 survivors

Saved-artifact audit passes: 62 rows, all 31 selected properties, both methods, exact frozen binary/source/input pins, terminal hashes and bounded independent validation evidence. All 23 definitive answers have independently checked reachable witnesses.

| Method | Solved /31 | Method-only solves | Unknown |
|---|---:|---:|---:|
| walk-guided | 14 | 8 | 17 |
| relaxed-batched | 9 | 3 | 22 |

The union solves 17/31; 6 are solved by both and 14 remain unresolved. This union combines separate five-second invocations; it is not a measured five-second portfolio.

Both methods used the exact earlier optimized diagnostic binary, original PNML/XML, strict five-second whole-property deadlines, sampled 2 GiB RSS and separate bounded checking. Neither used buffer agglomeration. Query order was frozen, with the first method alternating (16 versus 15 first positions).

## Complementary queries

walk-guided:

- `RERS17pb114-PT-5__RC06`
- `RERS17pb114-PT-5__RC07`
- `RERS17pb114-PT-5__RC13`
- `RERS17pb114-PT-9__RC05`
- `RERS17pb114-PT-9__RC06`
- `RERS17pb114-PT-9__RC14`
- `RERS17pb114-PT-9__RC15`
- `ASLink-PT-05b__RC05`

relaxed-batched:

- `RERS17pb114-PT-5__RC08`
- `RERS17pb114-PT-5__RC15`
- `RERS17pb114-PT-9__RC02`

## Deadline and overhead evidence

The runner counts an answer only when the observed whole-invocation wall time is at most five seconds and independent validation succeeds. Empty or incomplete timeout output remains unknown. Saved logs contain no definitive JSON answers rejected solely for arriving after the deadline.

| Method | Complete JSON /31 | Empty/incomplete JSON | Median wall minus reported parse+solve | Solver total | Validator total |
|---|---:|---:|---:|---:|---:|
| walk-guided | 29 | 2 | 0.035s | 93.737s | 45.381s |
| relaxed-batched | 23 | 8 | 0.029s | 137.208s | 30.362s |

The timing difference includes startup, serialization, polling and process cleanup; it does not isolate one source of overhead. Late or killed searches may have made unreported internal progress, so absence of a saved witness is not a proof that search could never find one. Validator costs are outside the five-second solver budget.

All selected properties were unresolved by the first grouped-only screen. These diagnostics guide development and do not establish aggregate coverage, stable timing or generalization. The next integrated candidate needs the complete 368-property comparison. Full exact solved/unresolved query sets and failure flags are in `audit.json`.
