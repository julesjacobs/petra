# Independent replay on original FastForward sources

Added `scripts/fastforward_source_checker.py` and the standalone bounded driver
`scripts/check_fastforward_source.py`. No existing benchmark harness, runner,
converter or proof-checker file was edited. Solver execution and remote hosts
were not touched.

The source checker imports no conversion code. Its LoLA parser uses semicolon
statements and explicit transition sections; its formula parser builds a
Boolean syntax tree that is evaluated directly on the final source marking.
It does not expand targets through the converter's DNF implementation. Source
zero-weight arcs remain semantically zero; exact-zero predicates remain exact.

Before replay it verifies:

- Frozen acquisition, source, mapping and canonical branch hashes.
- A bijection from canonical place/transition IDs to original source IDs.
- Every initial count and every weighted pre/post arc against the original
  LoLA, including read arcs and source transitions.
- Every transition's original enabling condition and update with Python
  arbitrary-precision integers.
- The original source EF formula, including all equality-zero constraints.
- The claimed final marking, when supplied.

The canonical target is deliberately not sufficient for acceptance: even a
weakened canonical target cannot certify a trace rejected by the source formula.
This checker certifies positives only. It does not certify negative proofs or
establish source/canonical target equivalence for negative answers.

## Verified evidence

Eight test groups pass normally and with `python3 -O`. Coverage includes
weighted read arcs, source/target forgery, permuted bijections, disabled traces,
invalid indices/types, forged final markings, counters above 64 bits, temporal
scope, hashes, deadlines, work limits, and original-property output wrappers.

`research/fastforward-independent-source-mapping-audit.json` records independent
source parsing and exact canonical-net correspondence for **all 218 queries**.
Every canonical branch hash and all 654 source/mapping file hashes matched.
This audit parses source formulas but does not assert their equivalence to the
canonical targets on every marking.

Six existing positive proposals from `results/linux-fastforward-smoke-v1` were
rechecked against original source files, in separately bounded local workers:

| Query | Frozen predecessor | Candidate |
|---|---:|---:|
| coverability: leabasicapproach | 4-step witness accepted | 4-step witness accepted |
| random_walk: mesh3x2_multi_100_0 | 39-step witness accepted | 39-step witness accepted |
| sypet: geometry10 | 2-step witness accepted | 2-step witness accepted |

All six pass. Results, requests, logs and worker resource observations are in
`results/fastforward-original-source-replay-v1`. This is additional validation
of existing results, not six new solver runs or a timing comparison.

## Integration contract

Create a JSON request containing `corpus`, `source`, `query`, `answer`, and
optionally `branch` for a direct backend outcome. The checker also accepts an
`original-property-v1` wrapper. Use `manifest_sha256` to pin the converted
corpus explicitly. Optional limits are `seconds` (30), `memory_mib` (2048),
`max_work` (200 million), and `max_file_bytes` (256 MiB).

```
vendor/venv/bin/python scripts/check_fastforward_source.py \
  --request request.json --response new-source-validation.json
```

The parent driver uses the existing portable process-tree runner. Its wall
limit kills the worker; memory enforcement is sampled RSS, not a Linux cgroup.
Resource exhaustion becomes unknown. Malformed inputs/witnesses become error.
Only a response containing `verdict: reachable` and
`independent_check: python-original-lola-witness` certifies the positive.
Checking time is explicitly excluded from solver timing. Existing response
paths are not overwritten.

For a later harness revision, invoke `check_artifact(request)` inside its
bounded original-input validation worker after the normal positive branch
check. Freeze both new checker files and the source acquisition with that
harness revision. The current frozen harness is unchanged.

## Complete-run batch replay

`scripts/replay_fastforward_results.py` audits a complete measured matrix, selects every native positive, and runs the independent original-LoLA driver in separate bounded workers. It records all selected outcomes, source/result hashes, and snapshots the checking scripts. This adds validation evidence without changing benchmark verdicts or timings. The frozen batch driver passed all six saved smoke positives in `results/fastforward-batch-replay-smoke-v2`; v1 remains preserved from before adding script snapshots. Full-run replay is pending completion and retrieval of the Linux comparison.

```
vendor/venv/bin/python scripts/replay_fastforward_results.py \
  --corpus benchmarks/fastforward-import-v2 \
  --source benchmarks/fastforward-repository-v1 \
  --results results/linux-fastforward-shared-relevance-v1 \
  --output results/fastforward-original-full-replay-v1
```
