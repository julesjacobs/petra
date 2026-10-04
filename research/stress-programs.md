# Frozen SER stress sources

`benchmarks/stress-programs/manifest.json` freezes 18 deterministic source programs and hashes. `SHA256SUMS` covers the manifest and every source. The generator imports the existing `counter`, `replicas`, and `monitor` functions in `scripts/generate_harder.py`; source syntax and existing corpora are unchanged. Provenance includes both generator hashes and the semantic-argument document hash. Regeneration verifies byte-for-byte equality and refuses to overwrite a differing existing directory.

| Family | Parameters | Sources | Previously generated bridge sources |
|---|---|---:|---:|
| Cyclic counter | domain/stages 31/16, 63/32, 127/64; locked and racy | 6 | 31/16 pair |
| Replicated register | 8, 10, 12 cells; locked and racy | 6 | 8-cell pair |
| Phase monitor | domain/cycles 4/64, 4/128, 4/256, 5/128, 5/256, 5/512 | 6 | none |

The four bridges exactly duplicate sources in `benchmarks/scaling-programs`; their paths are recorded in `exact_source_overlaps`. They must not be counted as four additional independent tests. All 18 cases are parameter-related to earlier families; the manifest deliberately marks them `independent_test: false`. There are 14 newly generated parameter cases, not 14 independently sampled families.

Source-level expectations are separate from `solver_result`, which is null throughout this source manifest. Locked counters/registers are expected serializable by the lock-linearization argument; racy counters/registers and phase monitors are expected nonserializable by the semantic constructions in `research/harder-programs.md`. These are not independently executed source-semantics proofs, raw-net certificates, or new benchmark outcomes.

For monitors, an observer returning 100 requires at least `domain * cycles` source `advance` requests from the zero initial phase: **256, 512, 1024, 640, 1280, 2560**, respectively. These are advancement counts, not Petri-net trace lengths. Completing an observer requires crossing each intervening cyclic phase, even if other requests were started earlier. A corresponding schedule achieving the bound exists by advancing once between successive observed phases. Counter/register cases do not have an analogous numeric minimum recorded.

## Ready commands

Source generation alone:

```sh
python3 scripts/generate_stress_programs.py
```

When current measurement jobs finish, collect a bounded initial frontend probe, preserving partial artifacts:

```sh
vendor/venv/bin/python scripts/collect_stress_raw.py \
  --output benchmarks/raw-stress-probe-v1 \
  --seconds 60 --memory-mib 2048 --artifact-mib 3072 \
  --case counter_d31_s16_racy \
  --case counter_d31_s16_locked \
  --case replicas_n8_racy \
  --case replicas_n8_locked \
  --case monitor_d4_c64
```

Collect the full frozen selection separately, if resource evidence supports doing so:

```sh
vendor/venv/bin/python scripts/collect_stress_raw.py \
  --output benchmarks/raw-stress-v1 \
  --seconds 120 --memory-mib 2048 --artifact-mib 3072
```

The collector refuses an existing output directory, verifies input source hashes, snapshots its runner source, records the frontend binary hash and command, and keeps all frontend work files. Each attempted case is recorded before launch and finalized separately; timeouts, memory limits, errors, and interruptions remain visible. It uses the existing process-tree runner's wall limit, sampled aggregate RSS limit and descendant cleanup. It refuses to start while that runner detects workspace builds/solvers. This detector is a local guard, not an inter-host scheduler; the operator must also wait for relevant remote measurement work before launching work on that host.

Collection writes its own manifest format `ser-stress-collection-v1`; it does not masquerade as the older `collect_raw.py` manifest. Successful exit plus an emitted file is labeled `exported-unvalidated`. Artifact hashing is streamed and the collector does not load a potentially enormous JSON document into its parent process. The bounded pipeline described below validates exported JSON/schema semantics in each worker invocation and consumes these retained query paths directly. Failure artifacts remain under each case's `work/` directory. No frontend export or solver invocation was performed when this ladder was frozen, and the collection script had not yet been executed or tested at source freeze time.

## Difficulty and resource limitations

Larger source parameters do not guarantee harder reachability instances. The raw SER frontend must still construct the serial semilinear union to define the query; avoiding complement construction does not avoid that earlier cost. Counter domains enlarge finite-state data, replica counts enlarge possible responses and the source's repeated-addition expression, and monitor counts enlarge continuation/control structure. A frontend timeout or oversized semilinear target measures frontend construction difficulty, not backend reachability difficulty. Report source count, attempted exports, validated exports, exporter failures, artifact sizes and solver outcomes separately.

The memory cap is a **sampled process-tree RSS safeguard**, not a Linux cgroup hard limit. Peaks between samples and short-lived children may escape accounting. The collector now has a separate collection-local sampled artifact guard (`--artifact-mib`, default 3072) covering each case’s source, log, and work files. It stops the frontend and records `artifact-limit` when the sampled total exceeds the limit. This does not modify the shared process runner. It is not a filesystem quota: between-sample writes may exceed the threshold, and those partial artifacts are deliberately retained. Hashing and manifest bookkeeping occur outside the measured frontend invocation. For strict publication collection, run inside a Linux cgroup with a memory limit and a disk quota, retaining the same attempt manifest. This script does not claim to provide those stronger host-level controls.

## Bounded raw validation and solver pipeline

`scripts/benchmark_stress_raw.py` now consumes `ser-stress-collection-v1` directly. Its parent reads only size-bounded manifests and worker summaries; it never parses raw queries or solver traces. It streams and checks query hashes while creating frozen input copies, snapshots the worker, process runner and direct raw-Z3 baseline, and copies the supplied frozen native binary into a fresh output directory. An existing output directory is rejected.

Each invocation launches `raw_stress_worker.py` under one outer wall/RSS guard. The invocation includes worker startup, input hashing, JSON parsing and schema checks, solver startup/parsing/search, trace parsing, exact original-net replay, and independent Z3 checks of nonmembership in every original serial linear set. The default solver phase gets 80% of the remaining time, reserving the rest for checking; `--solver-fraction` is recorded and configurable. No fixed extra verification grace period is added. The parent conservatively rejects a result when total observed invocation time, including cleanup, exceeds the outer deadline. Sampled aggregate RSS includes both the worker's parsed query and its solver child.

A positive answer is accepted only after exact replay reaches a completed marking and Z3 returns UNSAT for every supplied serial component. Z3 UNKNOWN, checker deadline exhaustion, and worker termination all produce explicit unknown statuses. Serial membership, malformed traces, marking mismatches and invalid input schemas are recorded separately. Negative claims are currently unsupported and become unknown; this runner does not claim to check future raw-negative certificates.

All sources in the collection’s recorded `selected_sources` remain visible by default, including selected sources not yet attempted when collection was interrupted. `--all-sources` explicitly expands the denominator to the full frozen ladder. Legacy collections without `selected_sources` use the full source manifest. Export timeouts and memory limits are **not run** entries, distinct from solver unknowns. `--case NAME` can restrict the source denominator explicitly. Reports show the full denominator, unavailable inputs and invocation-status counts. Bridge overlap and source expectations remain metadata. Solver results never overwrite source expectations.

After bounded frontend collection, run:

```sh
vendor/venv/bin/python scripts/benchmark_stress_raw.py \
  --corpus benchmarks/raw-stress-probe-v1 \
  --output results/raw-stress-probe-v1 \
  --binary results/solver-local-v1/vass-reach \
  --methods raw-bfs raw-potential raw-z3 \
  --seconds 10 --memory-mib 2048 --repeat 3
```

The binary argument must identify the intended frozen artifact available on this host; it is copied and hashed. Defaults are `raw-bfs raw-potential`. The probe defaults to its five recorded selected sources. Use `--all-sources` to include all 18 ladder sources, recording the other 13 as `not-collected`; `--case` chooses an explicit denominator.

Check the pipeline independently of production corpus generation:

```sh
vendor/venv/bin/python -m unittest discover -s scripts -p test_raw_stress_pipeline.py -v
```

Tests exercise failure denominators, unattempted sources, malformed schema and duplicate JSON fields, false/serial witnesses, forced Z3 UNKNOWN, changed input/manifest hashes, output overwrite refusal, killed workers with a partial positive file, and a complete synthetic subprocess solve/check. These are harness tests, not timings or evidence of solver performance on the stress corpus. Test evidence is recorded in `research/raw-stress-pipeline-tests.log`.

The collection manifest records `selected_sources` before the first attempt, so interruption does not erase the intended selection. The benchmark runner honors this recorded selection by default and keeps its unattempted sources explicitly `not-collected`; `--all-sources` exposes the full ladder and `--case` chooses an explicit selection.

After the host is free, test the newly added sampled artifact guard before collection:

```sh
vendor/venv/bin/python -m unittest discover -s scripts -p test_stress_artifact_guard.py -v
```

The raw pipeline’s 11 synthetic tests passed before local collection resumed. The two artifact-guard tests were written afterward and have **not yet run** because local measurement/collection work is active.

The initial five-source probe completed successfully after the frozen evaluation: all five emitted raw queries in0.14–8.57s,0.7–8.7MB. See `research/stress-collection-results.md`. The bounded raw pipeline passed11tests and the artifact guard passed2tests; logs are retained. Full collection and actual solver difficulty remain pending.

The pipeline now also copies original `.ser` sources and available frontend logs into its artifact. Exported-query runs require the source bytes to match the frozen source hash, not merely matching hash strings in two manifests. Collection/manifests are checked for mutation while snapshots are prepared. Family/parameters, exact export attempts, bridge provenance and source expectations remain in `sources.json`.
