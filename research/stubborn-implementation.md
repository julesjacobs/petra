# Opt-in stubborn-set witness search

Implementation: `src/relaxed.rs`, its private tests in
`src/relaxed_stubborn_tests.rs`, and dispatch in `src/main.rs`.
Preservation argument: [stubborn-preservation-review.md](stubborn-preservation-review.md).
This implementation has no measured performance result yet.

`relaxed-stubborn` runs the same helpful-only first attempt as `relaxed-focused`,
with the same one-third time allocation. Only its unrestricted fallback uses
stubborn-set reduction. `portfolio-stubborn` uses the same capacity discovery,
relevance slicing, causal phase, local closure phase and remaining search
schedule as `portfolio-focused`. Existing defaults and state limits are unchanged.

The seed is the **first enabled transition in the existing helpful-first order**.
If that transition changes target support, use full expansion; do not skip a
preferred visible transition to select an invisible seed. Closure uses per-place
reader, net-negative consumer and net-positive producer lists, without a
quadratic transition dependency table. Weighted guards determine disabledness.
An enabled member adds symmetric disabling dependencies; a disabled member adds
all net-positive producers of one deficient place. Only a complete closure can
reduce the enabled set. Every enabled selected transition must leave every place
in every signed/equality target's support unchanged.

The fixed parameters are K=8 and 100,000 closure work items. Work items count
popped members, inspected guards and visited dependency entries, including
repeats. Closure work or time exhaustion selects full expansion; the surrounding
search still observes its global deadline. Full expansion occurs every eighth
fixed discovery depth and whenever any selected successor was previously seen.
The freshness checks happen before inserting any successor. Duplicate fresh
successors share that snapshot. Depth arithmetic is checked; overflow returns
unknown. Selected transitions preserve helpful-first order. Every positive
answer is replayed on original transitions; exhaustion still returns unknown.

## Diagnostics

Set `VASS_RELAXED_PROFILE=1` or `VASS_PORTFOLIO_PROFILE=1`. Each search attempt emits
one JSON line to **stderr**, including unknown and early-return outcomes:
`{"event":"relaxed-search","stats":{...}}`. The helpful attempt has
`focused=true, stubborn=false`; a reduced fallback has
`focused=false, stubborn=true`. The JSON answer/proof schema is unchanged.
Redirect stderr separately from stdout when benchmarking.

- `expanded`: nodes selected for expansion after computing their relaxed plan.
- `generated`: new successors inserted into the seen set, excluding the initial
  marking. The accepted witness successor is included.
- `chosen`: successful enabled firings processed, including duplicate successors
  and a successor rejected by the state cap.
- `enabled_considered`: enabled transitions found among those whose enabledness
  was inspected. POR-on scans the enabled set before selection. POR-off and the
  helpful-only attempt retain their original lazy iteration and can stop early;
  this counter is not an exhaustive enabled-alphabet count on those paths.
- `reductions`: expansions that pass every reduction guard.
- `full_periodic`, `full_visible`, `full_seen`, `full_closure_limit`,
  `full_all_enabled`: full-expansion reason counters. `full_visible` also covers
  no enabled seed. Only POR-on uses these counters.

The original lazy expansion order is preserved when reduction is off, with no
new alphabet scan, dependency index, successor materialization or duplicate guard
check for instrumentation. The same counters are maintained on both paths.
Counters describe completed work and may include an incomplete final expansion.

## Verification

Ten new private tests cover weighted necessary enabling, read-loop exclusion,
symmetric read/consumer dependence, seen loops and merged successors, duplicate
fresh successors, signed/equality visibility, unbounded acyclic postponement,
K=1, work/deadline exhaustion, depth overflow, and seed ordering. A direct
unrestricted-search differential test checks 160 generated bounded nets against
exhaustive BFS and replays every reported witness. Existing relaxed integration
tests now exercise all three public variants.

The first `cargo test` completed successfully: 358 passed, one pre-existing
ignored test, zero failures. A subsequent diagnostics smoke caught extra records
from a temporary default value being dropped; explicit initialization removes
that temporary. A CLI regression checks exactly one record per attempt and
checks counters on unknown outcomes. The final full suite passed: **359 passed,
one pre-existing ignored, zero failures**. Final Clippy with
`cargo clippy --all-targets -- -D warnings` passed. Existing vendored Varisat
warnings remain; no project warnings were emitted. The subsequent extended capacity and relevance CLI tests passed,
exercising `portfolio-stubborn` on original PNML/XML with capacity preprocessing
on/off and checking lifted witnesses/proofs on JSON input. Logs are in
`results/stubborn-validation-v1/`. No benchmarks, remote actions, held-out
queries or performance claims are part of this implementation handoff.

The final release build and formatting check passed. Both release variants'
unknown-outcome diagnostic probes emit exactly two valid records with the
expected attempt flags and counts. The pre-fix four-record output is preserved
as `relaxed-focused-before-diagnostics-fix.jsonl`. Final release SHA-256:
`7277cdfa4bd16cc2e75649bdd9bd3558a9942ec03a5e1bd805b960f5b3d4cbb6`.
All validation processes are terminal; no benchmark process was started.
