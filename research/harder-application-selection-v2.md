# Application parameter ladders v2

Frozen **29 new instance names / 464 planned ReachabilityCardinality property slots** in `benchmarks/application-parameter-ladders-v2-selection.json`. These are development candidates for measuring where solvers stop scaling; their difficulty is unmeasured. No acquisition, import, solver run, or remote operation was performed.

Selection SHA-256: `e729cd00a2facdddcb0273dda32915b0f5a78f17d6e70185a1cb172a80fec605`.

The publication-development stress selection and the six-family application expansion already include their final indexed instances. Five original application-development families still have later indexed instances absent from the recorded corpus metadata. This selection takes **all** such instances, preserving a parameter ladder instead of choosing one extreme. DoubleExponent is excluded from this application cohort because it is a synthetic complexity family; its scaling should be reported separately.

| Family | Previously selected name parameters | New name parameters | Models / slots |
|---|---|---|---:|
| FMS | 2, 10 | 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000 | 11 / 176 |
| DatabaseWithMutex | 2, 10 | 20, 40 | 2 / 32 |
| RwMutex, fixed r=10 | w=10, 50 | w=100, 500, 1000, 2000 | 4 / 64 |
| RwMutex, fixed w=10 | r=10 | r=20, 100, 500, 1000, 2000 | 5 / 80 |
| SharedMemory | 5, 20 | 50, 100, 200 | 3 / 48 |
| TokenRing | 5, 15 | 20, 30, 40, 50 | 4 / 64 |

The cohort covers manufacturing coordination (FMS), database exclusion, reader/writer exclusion, shared memory, and ring coordination. These domain labels are conventional interpretations of the existing family names. The numeric labels above are parsed from names; model dimensions have not been independently checked. In particular, RwMutex changes two different parameters and must be plotted as two ladders. Increasing parameters or published ordinals does not establish increasing runtime. Different MCC instances may also carry different generated properties: this is a family/parameter ladder, not a claim that one fixed property is preserved across sizes.

## Deterministic selection and denominator

Use the local `vendor/mcc2021/index.html`, SHA-256 `58b01d6b01987ef8b4d8fada40b5d392913eb9e3e2fd6ab5dfceded4fbb5fe3f`, from `https://yanntm.github.io/pnmcc-models-2021/`. Extract PT archive names in source order, deduplicating at first occurrence. For each of the five named families, find the largest ordinal already selected for development in `mcc-selection.json`, `publication-selection.json`, `stress-selection.json`, and `application-expansion-v1-selection.json`. Select every later ordinal. No solver outcome or property polarity enters this rule.

The five families contain **44 indexed instances**: 10 prior selections, five earlier unselected instances, and 29 eligible later instances. The five earlier instances remain explicitly excluded by the ordinal rule; every eligible later instance is selected. The machine-readable artifact records every indexed instance and decision, prior selection hashes, source URLs, source ordinals, parsed name parameters, and all 16 planned slots per model.

All **464 slots remain in the acquisition and comparison denominator**, including missing archives, unsupported syntax, unexpected property counts, import timeouts, resource limits, solver failures, and unknown answers. Do not silently replace or remove failures. Report per-family and per-parameter results, along with the full denominator. These are development data; tuning on them cannot support a held-out evaluation claim. Keep the existing smaller instances as separately identified baseline points without counting them again as new inputs.

## Reservation and overlap audit

All 22 reserved/evaluation families are excluded: AirplaneLD, Angiogenesis, BusinessProcesses, CloudDeployment, DES, Diffusion2D, ERK, HirschbergSinclair, Kanban, LamportFastMutEx, LeafsetExtension, ParamProductionCell, Peterson, Philosophers, Raft, ResAllocation, ShieldPPPs, SmartHome, Sudoku, SwimmingPool, TCPcondis, TwoPhaseLocking.

The artifact inventories and hashes 34 existing metadata files: immediate corpus manifests, root selection/reservation files, and immediate `selection.json` files. None contains an exact selected instance name. This is an exact-name metadata audit, not a graph-equivalence or renamed-model audit. Only metadata was read; no reserved model, property, archive, or solver result was inspected. After acquisition, record source archive/input hashes and audit exact/canonical duplicates, including overlap with the FastForward corpus. Preserve full-denominator and duplicate-aware results separately.

## Proposed bounded acquisition

The existing collector accepts this manifest directly. This invocation is ready but **has not been executed**:

```sh
vendor/venv/bin/python scripts/collect_stress_mcc.py \
  --selection benchmarks/application-parameter-ladders-v2-selection.json \
  --output benchmarks/application-parameter-ladders-v2 \
  --seconds 120 \
  --memory-mib 2048 \
  --archive-mib 256 \
  --expanded-mib 1024 \
  --artifact-mib 1024
```

One worker runs at a time, with a nominal 58-minute total worker budget plus orchestration and cleanup. Each model has a 120-second acquisition/import budget, sampled 2 GiB RSS ceiling, 256 MiB compressed archive limit, 1 GiB expansion limit, and 1 GiB retained-artifact limit. Maximum retained model artifacts are therefore 29 GiB plus logs and metadata. Linux also sets a 2 GiB address-space limit; macOS RSS enforcement is sampled. The collector checks for conflicting workspace workloads, refuses an existing output directory, snapshots its source/runtime, preserves partial files and all failed slots, and runs no solver.

Run collection only after live local measurement/build work has finished. The source-index hash freezes selected names and URLs, not remote archive bytes. Acquire first, validate imported semantics and provenance, then freeze single-core solver configurations and a common budget before measuring. Only those measurements can show whether this selection is harder than the current test set.

## Collection handoff

The preceding text records the preregistration state. Root subsequently reported starting the exact frozen selection with the recorded limits in local session 61362. Selection bytes are unchanged. This note does not independently verify collection completion, imported semantics, duplicates, or solver difficulty; those require the postcollection audit.
