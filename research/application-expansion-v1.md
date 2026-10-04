# Application expansion v1: preregistered development selection

Frozen **six new named families, 12 PT instances, 192 property slots** in
`benchmarks/application-expansion-v1-selection.json` before acquisition or
solver execution. Selection SHA-256:
`65524b6d4faeebd2b5243986a23cac23ce59dec3668a60988d82d917302507d5`.

The existing local MCC 2021 index is the only instance source. Its SHA-256 is
`58b01d6b01987ef8b4d8fada40b5d392913eb9e3e2fd6ab5dfceded4fbb5fe3f`.
For each named family, deduplicate indexed PT names at first occurrence and
choose one-based ordinals `ceil(3*N/4)` and `N`. This samples two later published
instances, including the final one. **Published order is not a verified measure
of net size, reachability difficulty, or novelty.** No results or property
polarities informed this selection.

| Family / domain rationale | First selected instance (ordinal) | Second selected instance (ordinal) |
|---|---|---|
| BART / rail transport control | BART-PT-040 (6/8) | BART-PT-060 (8/8) |
| CircadianClock / biological clock | CircadianClock-PT-010000 (5/6) | CircadianClock-PT-100000 (6/6) |
| IOTPpurchase / electronic purchase protocol | IOTPpurchase-PT-C05M04P03D02 (3/4) | IOTPpurchase-PT-C12M10P15D17 (4/4) |
| NoC3x3 / network-on-chip communication | NoC3x3-PT-6B (12/16) | NoC3x3-PT-8B (16/16) |
| RobotManipulation / robotics | RobotManipulation-PT-01000 (10/13) | RobotManipulation-PT-10000 (13/13) |
| SmallOperatingSystem / operating-system coordination | SmallOperatingSystem-PT-MT2048DC1024 (15/19) | SmallOperatingSystem-PT-MT8192DC4096 (19/19) |

These add application domains/model families beyond the current concentration
on CAN, DLC, GPU progress, JoinFreeModules, and existing mutex/database nets.
Domain descriptions follow the family names and conventional interpretations;
no new model documentation was downloaded. BART versus CircularTrains and
CircadianClock versus ERK are different named families, not an assertion that
all underlying modeling techniques or generators are independent.

## Exposure and reservation audit

Inventoried 29 local metadata files: immediate `benchmarks/*/manifest.json`,
root selection/reservation JSON files, and `benchmarks/*/selection.json`.
The selection records every file hash and its family inventory. There are 36
previously recorded MCC family names, including selection-only reservations;
this count does not assert that all were benchmarked. None of the six selected
families occurs there. Their exact family strings are also absent from prior
query/instance names and FastForward source-LoLA metadata. This does not rule
out renaming, related models, or undocumented historical exposure.

All **22 evaluation families** remain excluded:

- Newly reserved: Angiogenesis, BusinessProcesses, DES, Diffusion2D,
  ParamProductionCell, Raft, ResAllocation, SmartHome.
- Earlier evaluation: AirplaneLD, CloudDeployment, ERK, HirschbergSinclair,
  Kanban, LamportFastMutEx, LeafsetExtension, Peterson, Philosophers,
  ShieldPPPs, Sudoku, SwimmingPool, TCPcondis, TwoPhaseLocking.

Only reservation/manifest metadata was read. No reserved archive, PNML model,
property payload, or solver output was inspected. This expansion is explicitly
**development data**, never a replacement for the reserved evaluation set.

## Ready collector invocation

The selection uses the existing collector's exact schema:
`format=mcc-stress-selection-v1`, `split=stress-development`, and 16 properties
per model. The runnable command below is proposed; it was **not executed**:

```sh
vendor/venv/bin/python scripts/collect_stress_mcc.py \
  --selection benchmarks/application-expansion-v1-selection.json \
  --output benchmarks/application-expansion-v1 \
  --seconds 120 \
  --memory-mib 2048 \
  --archive-mib 256 \
  --expanded-mib 1024 \
  --artifact-mib 1024
```

Run only on a host without live measurements or builds. The collector checks
for conflicting workspace processes and creates one worker at a time. Limits
are per model: 120 seconds including acquisition/import, sampled 2 GiB RSS,
256 MiB compressed archive, 1 GiB archive expansion, and 1 GiB retained
archive/extracted/canonical artifacts. Linux additionally sets a 2 GiB address
space limit; macOS memory checks are sampled, not a hard allocation ceiling.
Twelve workers give a nominal 24-minute work budget plus orchestration/cleanup;
the retained-artifact cap is at most 12 GiB for model artifacts plus logs and
metadata. This is collection accounting, not solver performance measurement.

All sixteen `ReachabilityCardinality` slots per model remain in the denominator
on download failure, unsafe/unsupported archive or model syntax, missing or
unexpected property count, timeout, memory exhaustion, or artifact limit.
Retain failures and partial files; do not replace a difficult or unavailable
selection with an easier instance. The collector refuses to overwrite an
existing corpus and records archive checksums, its source snapshot, runtime,
per-model limits, and per-slot collection status.

The index hash fixes selected names, not the remote archives' bytes. Archive
hashes, dimensions, property support, licenses, duplicate relationships, and
actual difficulty remain unobserved until acquisition/audit. No download,
import, build, solver run, timing, or remote action was performed for this plan.

## Collection completed

Root executed the registered collection command locally. Session50363 exited0; all192/192 properties imported. Archive/input hashes were audited, with892 unique input files/174,726,804bytes and five exact branch-hash duplicate pairs (187 representatives). No solver has run on this suite yet. See application-expansion-v1-verification.json and benchmarks/application-expansion-v1/README.md. The preceding acquisition instructions record the preregistration state.
