# Larger MCC development instances

`benchmarks/stress-selection.json` freezes 23 models and 368 planned ReachabilityCardinality property slots from the eight existing publication-development families. Selection uses only the cached published index and prior selection, whose hashes are recorded. For each family it chooses the last three published PT instances strictly after the greatest previously selected ordinal (CircularTrains has only two). No solver outcomes were inspected for selection. Later published ordinal is the specified selection rule; it is not yet evidence that these properties take longer to solve.

The set is **stress-development**, not independent held-out evaluation. The selection is immutable: the generator refuses an existing output, and the collector stores download hashes in a separate archive-checksums file.

Implementation files are `scripts/select_stress_mcc.py`, `scripts/collect_stress_mcc.py`, and their `test_stress_*.py` tests. No downloads, archive extraction, import, or tests have been run while existing measurements are live. Only the small metadata selection generator was executed.

The collector creates one worker per model, sequentially. Each worker owns download, streaming checksum, safe archive extraction and semantic import with the existing `smpt_import` functions. Defaults: 120 seconds/model; 2GiB sampled RSS cap; additionally a 2GiB address-space hard limit on Linux; 512MiB compressed archive cap; 2GiB total expanded member cap. It extracts only original PNML and ReachabilityCardinality XML, rejects unsafe paths, links, devices, sparse members and duplicate required members, and refuses an existing corpus. It snapshots importer and collector hashes.

All 368 slots remain in the manifest even if a model times out, exhausts memory, fails to download or cannot be imported. Unknown slots have `observed=false` and no invented property ID or polarity. Observed XML IDs survive net-import failure through per-model progress metadata. Successful property imports use the existing canonical manifest layout. Every model has a collection outcome with exit code, time, sampled RSS, resource limits, completed stage and error. Archive hashes and downloaded originals remain separate from selection. These collector guarantees are implementation intent pending the tests below.

When local and Linux timing runs are terminal, validate first:

```
vendor/venv/bin/python -m unittest discover -s scripts -p 'test_stress_*.py' -v
```

Then collect on an idle host (copy the frozen selection and required scripts/importer if using Linux):

```
vendor/venv/bin/python scripts/collect_stress_mcc.py \
  --selection benchmarks/stress-selection.json \
  --output benchmarks/mcc-stress-development \
  --seconds 120 --memory-mib 2048 --archive-mib 512 --expanded-mib 2048 --artifact-mib 3072
```

The actual failed-import/resource denominator must be reported with solver results. Resource-limit failures do not justify silently selecting smaller replacement instances. An import failure may require a subsequent separately recorded collector revision or a native importer; preserve the original attempt.

## Collection safeguards

Each model now has a default **3GiB logical artifact-byte limit**, covering the compressed archive (including incomplete downloads), selected extracted PNML/XML, and every canonical property/net/JSON output, including partially written files. The limit is checked before each write. JSON uses incremental encoding and Tina text is emitted line by line; large artifacts never pass through the parent. Writes that would exceed the budget fail the model with `termination_reason=artifact-limit`; all sixteen property slots remain. The parent recounts on-disk artifact sizes after every worker, including killed workers, and records category totals and the budget in the outcome. Small collection logs, metadata and source snapshots are outside this artifact budget. For 23 models the default budget bounds counted artifacts at 69GiB; physical disk usage and metadata are separate.

A workload preflight runs before corpus creation and before every worker. It rejects active workspace solvers/builds and recognized Python benchmark/collector drivers, including drivers between invocations. This is a local-host check, not an exclusive reservation or a check of remote hosts; callers must still coordinate benchmark and collection launches. If a workload appears between workers, collection stops with unattempted slots retained in the incomplete manifest.

`collector-source/` stores the actual collector, semantic importer and workload-guard source files. `collector-provenance.json` records their hashes, Python executable/path/hash/version/prefix, platform and psutil version. Sources are rechecked before every worker. Tests were extended for bounded writes, preservation of failed-property denominators with measured byte totals, streamed Tina equivalence, provenance files and mocked active-workload rejection. All 16 collector and selection tests passed after local evaluation finished; see `research/stress-collector-tests.log`. Collection started in session15635 with the command above; results are pending.
