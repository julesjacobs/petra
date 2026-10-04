# Solver and benchmark improvement at five seconds

**The integrated candidate solves 363/368 original properties in both complete repetitions, versus 323 and 322 for the frozen baseline. There are 40 gains reproduced in both runs and zero losses.** All 1,371 definitive answers passed separate bounded independent checks against the original PNML/XML. All 1,472 scheduled invocations are retained.

| Cohort | Slots | Baseline, repeats 1 / 2 | Candidate, repeats 1 / 2 |
|---|---:|---:|---:|
| Existing development cohort | 176 | 136 / 135 | 175 / 175 |
| Six-family expansion | 192 | 187 / 187 | 188 / 188 |
| Combined | 368 | 323 / 322 | 363 / 363 |
| Combined ordered-branch representatives | 366 | 322 / 321 | 361 / 361 |

The candidate solves the same 363 slots in each run. Baseline RERS17pb114-PT-9 RC07 changes from reachable in 2.926 seconds to a 5.018-second outer timeout; this observation is retained. Paired gains are 40 and 41, with 40 common to both repeats. The representative view has 39 gains common to both repeats. Unknowns fall from 45/46 to five.

## Where coverage improves

| Family | Slots | Baseline, repeats 1 / 2 | Candidate, repeats 1 / 2 |
|---|---:|---:|---:|
| ASLink | 32 | 28 / 28 | 29 / 29 |
| ClientsAndServers | 32 | 32 / 32 | 32 / 32 |
| CloudReconfiguration | 32 | 32 / 32 | 32 / 32 |
| DNAwalker | 32 | 18 / 18 | 32 / 32 |
| HouseConstruction | 32 | 32 / 32 | 32 / 32 |
| IBM319 | 16 | 16 / 16 | 16 / 16 |
| MAPK | 32 | 32 / 32 | 32 / 32 |
| NQueens | 32 | 32 / 32 | 32 / 32 |
| RERS17pb114 | 32 | 6 / 5 | 31 / 31 |
| Railroad | 32 | 31 / 31 | 31 / 31 |
| RefineWMG | 32 | 32 / 32 | 32 / 32 |
| TriangularGrid | 32 | 32 / 32 | 32 / 32 |

The 40 repeated gains comprise fourteen DNAwalker properties, twenty-five RERS properties, and ASLink-PT-05b RC05. The gains are concentrated in these three families. The earlier grouped-only candidate solved 337/368 in its own screen; its binary and results are distinct and are not pooled into this comparison.

## Implementation

- [Grouped excess](../grouped-excess-2026-10-04/theory.md) proves negative answers by bounding the sum of token mass above group thresholds. Induction and target exclusion are checked exactly, with a separately implemented Python checker.
- [Divided-marking witnesses](../scaled-witnesses-20261004.md) search from a common divisor of the initial marking without changing any transition arcs. A positive word is repeated, expanded and replayed on the original net and full signed target. A failed reduced search never refutes the original problem.
- The portfolio runs divided-marking guided walks and ordinary guided walks before optional reductions, then divided-marking relaxed search and previous fallbacks. This preserves the original-net ASLink witness that reduction changed in an intermediate diagnostic.
- Guided walks skip enabledness-user scans when no guard threshold can change. Relaxed search retains exact enabled actions and indexes sources and target effects. Count realization uses topological blocks when its producer/consumer graph is acyclic. Input validation reuses a place-membership table, and large arithmetic construction is bounded before starting.
- `--method auto` now chooses `portfolio-excess` for ordinary input and preserves `raw-potential` for raw input. Prior named methods remain selectable. The measured configuration explicitly enables buffer agglomeration and uses two million states/firings.

These are integrated changes. The selected diagnostics identify useful mechanisms but do not establish an isolated speed contribution for every implementation optimization.

## Cost, including verification

| Both repetitions, all slots | Baseline | Candidate |
|---|---:|---:|
| Solver wall time, summed | 634.198 s | 360.171 s |
| Independent validation, summed | 164.350 s | 345.667 s |
| Solver plus validation, summed | 798.548 s | 705.837 s |
| Mean solver PAR-2 | 1.495 s | 0.561 s |

Total solver-plus-validation time decreases by 11.6%, while validation cost increases because additional answers and longer expanded witnesses are checked. PAR-2 charges every unknown/failure ten seconds; it is a coverage-sensitive penalty, not common-case speed.

On the 322 queries solved by both methods in both repetitions, the geometric mean baseline/candidate ratio is 0.897 for solver time and 0.857 including checking. Thus the candidate is about 11.5% slower on this selected solver-only view and 16.7% slower including checking. Broader coverage is the primary gain; this is not a uniform speedup.

## Retained unsuccessful outcomes

| Repeat | Method | Unknown | Timeout flag | Nonzero exit flag |
|---|---|---:|---:|---:|
| 1 | baseline | 45 | 42 | 28 |
| 1 | candidate | 5 | 4 | 1 |
| 2 | baseline | 46 | 43 | 29 |
| 2 | candidate | 5 | 4 | 0 |

Timeout and nonzero-exit flags can describe the same invocation; they are not disjoint failure counts. Every such row remains unknown in the score. All accepted definitive rows have successful independent checks.

## Benchmark improvement and limits

The [192-property expansion](../benchmark-expansion-2026-10-04/README.md) adds ASLink, MAPK, HouseConstruction, Railroad, NQueens and ClientsAndServers, with two instances each. Selection was frozen before acquisition and solver outcomes. All original imports independently match; 191 ordered-branch representatives have no overlap with the earlier cohort. Combined reporting retains 368 slots and 366 representatives.

All new arcs have unit weights. The expansion adds model diversity and large initial counters, not weighted-arc coverage. It is mostly easy for the baseline: 187/192 were already solved. All 22 reserved evaluation families remain untouched. These are two local arm64 Mac development repetitions with sampled 2-GiB process-tree limits and no overlapping builds or solver measurements. They establish repeated checked coverage here, not held-out generalization, precise speed confidence intervals, novelty, or external-solver superiority.

## Unresolved and unsuccessful experiments

The same five properties remain unknown in both candidate repetitions:

- RERS17pb114-PT-5 RC12
- ASLink-PT-05b RC06
- ASLink-PT-10b RC05
- ASLink-PT-10b RC07
- Railroad-PT-100 RC09

Backward cover solved none of the 31 survivors in either of its two source versions and stays standalone. The earlier count-dominance experiment also had no benefit. A walk-heavy intermediate portfolio missed complementary relaxed-search witnesses; the next version still missed the ASLink witness after reduction. All diagnostic rows, failures, snapshots and audits remain available in the [first](../coverage-iteration-20261004/README.md), [direct-search](../direct-search-20261004/RESULTS.md), [second](../coverage-second-20261004/RESULTS.md), [third](../coverage-third-20261004/RESULTS.md), and [integrated survivor](../coverage-final-screen-20261004/RESULTS.md) records.

The [Pro consultation](https://chatgpt.com/c/6ac195da-cc4c-83eb-a123-e76ea2d22af5), obtained with the [Pro skill](/Users/julesjacobs/.codex/skills/pro/SKILL.md), proposes combining different one-copy endpoints for RC12. Its [assessment](../pro-coverage-20261004/assessment.md) distinguishes supplied evidence from independently reproduced results. After the campaign finished, the supplied 5,192-transition RC12 witness and both component words passed [independent original-input replay](../pro-coverage-20261004/rc12-independent-replay-v1/result.json), in 3.912 seconds of checking. This confirms a reachable target, but the candidate did not discover it; it remains unknown in the measured score. Combining different endpoints is a separate possible follow-up.

## Checks and reproduction

621 Rust tests passed, two were ignored, and Clippy passed before the final freeze. Grouped-excess and backward-cover Python checker tests passed; optimized-mode checker checks are retained. [Static integration review](../final-review-20261004/integration-review.md) found no actionable issues. `codex review -` could not start because this directory is not a Git repository; its logs are retained and no clean built-in review is claimed. Witness replay is not internally interruptible at every step, so the outer deadline and late-answer rejection remain necessary.

```sh
cargo build --release
./target/release/vass-reach --pnml model.pnml --xml properties.xml \
  --property-id QUERY_ID --method portfolio-excess --seconds 5 \
  --max-states 2000000 --buffer-agglomeration
```

Candidate binary SHA-256: `0f591ec86df357cac0ce175d26a9a77d59a69cc4bc51ec9bfe82a6543971b22e`.
Baseline binary SHA-256: `19ef799d463625b00fb779f77951ef2178dcd72bf768c8999659f1bcc5edc949`.
Frozen plan SHA-256: `b06c10b3a5554eea96eea26a5baabc7b934e6e09e392897dd0cd9fc006bc55bc`.

The [protocol](protocol.json), [plan](plan.json), [first audit](repeat1-audit.json), [second audit](repeat2-audit.json), [summary](summary.json), terminal receipts and frozen source/binary snapshots contain exact commands, ordering, hashes, accepted answers, validator requests/responses and all failures. The harness refuses replacement measurements; use a fresh campaign directory for another version.
