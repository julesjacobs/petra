# Geometric original-property schedule review

No semantic defect found in the reviewed scheduler and CLI/runner wiring.
The default remains SinglePass; Geometric selects the same SinglePass path for
zero or one branch. No production code was edited by this reviewer.

## Ordering, aggregation and checking

Each pass visits unresolved branches in ascending index order. Refuted branches
are cached; their targets and original net remain unchanged. The scheduler swaps
the current target into the reused net and restores it after each call. The branch
callback receives an immutable problem, and no input files are rewritten.

A repeated branch replaces its latest outcome rather than appending history.
Attempts stay a contiguous prefix after partial first passes and a contiguous
full vector on later passes. A later winning retry truncates at that branch,
removing stale higher-index outcomes. This satisfies the unchanged
original-property-v1 validator's rejection of duplicates, gaps, and entries after
a positive branch. A final negative requires full branch coverage; the validator
independently checks every retained refutation and downgrades unchecked ones.
EF reachability and AG counterexample polarity are preserved.

Whole-property time includes parsing. The scheduler checks before and after each
branch and again before aggregation; a late branch answer becomes Unknown and a
final expired clock censors even cached evidence. Independent validation never
upgrades a deadline-censored snapshot. The outer adapter also discards process
timeouts and wall time above the registered budget before invoking validation.
Canonical comparisons still cover unattempted branches after an early winner,
and original input hashes/mutation checks remain in force.

The initial geometric slice is max(1ns, floor(R/(2*n))); successive slices double
with saturation and a cap at initial R. The slice actually passed is also capped
by current remaining time. A full pass at the initial-R cap terminates, so a
stationary injected clock and immediately returning Unknown callbacks cannot
cause an infinite loop. Actual branch deadlines remain advisory: external process
limits are needed for a backend that does not return promptly.

## Performance and resource boundaries

- Ascending retries are not a fairness guarantee. An early branch can consume
  the remaining total budget on a later pass, preventing later branches from
  receiving that pass's larger slice. Repeated fresh solves may repeat work.
  These are experimental tradeoffs, not correctness defects.
- Capacity discovery remains cached from the first call, including an inconclusive
  discovery performed with a small first slice. Geometric retries do not retry
  that discovery. This may limit benefits without changing proof validity.
- Latest-outcome output bounds stored entries to one per branch, but does not
  preserve retry history for performance attribution. External profile evidence
  is needed to explain scheduling effects; final attempts alone are insufficient.
- Zero/single-branch fallback avoids gratuitous retries, but no general performance
  dominance or completeness result follows from the schedule.

## Prepared validation

`tests/original_schedule_cli.rs` has five real PNML/XML integration test groups:
negative coverage and EF/AG polarity; winning-prefix truncation; zero/single-branch
compatibility; all reduction flags together; and PNML-only/raw/unlimited argument
restrictions. Fixtures compare source bytes before/after calls and avoid
performance thresholds or assertions about speedups.

The CLI tests are prepared but not run here. Root should execute centrally:

```sh
cargo test --test original_schedule_cli
```

Seven local Python test groups passed:

```sh
python3 -m unittest discover -s scripts -p test_original_schedule_validation.py -v
```

They check cached-refutation/winner snapshots, unresolved earlier branches, full
independent negative coverage, rejection of history/duplicate/gapped results,
deadline censoring, canonical/source mutation, and outer-adapter censoring while
the geometric flag is present. These tests invoke no solver. Fake-clock scheduler
unit tests and Cargo validation are owned by the other agents.

No Linux access, transfers, builds, or measurements were performed here.

## Source identities at review completion

```text
src/original.rs 68dcf95839027575908025d4b62dd30759dc8450a8762274e4d054f2a66b4d1d
src/main.rs c80c0048c7d375fed3af7e43b53022355cd9ac0bea804e9b63d9a9ef610dc7be
scripts/rust_original_validation.py 09a247de7c2dbf95895292b8932e4172625f4a6cf432854cdc03a5e763af3fb9
scripts/benchmark_smpt_classic.py 02a20be10e03f97114a1abaee167a4e8ae12c279fedc50345ce02d55fefe3143
```
