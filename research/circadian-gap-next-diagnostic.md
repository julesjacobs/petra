# CircadianClock RC12: evidence and next diagnostic

The saved successful witness points to repeated-transition acceleration as a
more targeted next experiment than further branch-scheduler tuning. This is an
engineering proposal, not a measured improvement. No solvers, builds, proof
checkers or remote measurements were run for this note.

## Saved observations

- `results/geometric-branches-gaps-v1` contains twelve audited rows: three
  properties and four configurations. At the strict five-second local macOS
  deadline, control and geometric solve 0/3; buffer and combined solve 2/3.
  CircadianClock RC12 remains unknown in all four configurations. Profiling was
  disabled. Its raw outcomes are unvalidated diagnostic evidence because each
  row exceeded the strict outer deadline.
- The geometric Circadian output stops at branch 9 while retaining outcomes
  for branches 10 and 11. Together with the scheduler implementation this shows
  that a retry pass occurred. Branches 2, 6 and 10 were refuted by the causal
  state equation; the other nine remained unresolved. Latest outcomes replace
  earlier attempts, so the file does not reconstruct the complete schedule.
- In `results/application-budget-diagnostic-v1`, the older frozen Linux binary
  reports unknown with a five-second internal budget and reaches branch 0 with
  a sixty-second internal budget. The latter took 0.5555 seconds wall time;
  the focused relaxed phase took 0.3967 seconds after 0.1007 seconds of local
  closure. Its original-net witness was independently checked in the saved
  artifact. The five-second run's first focused phase exhausted its allocation
  after 0.2424 seconds. These runs enabled profiling and allowed two seconds of
  outer grace; they are diagnostic measurements, not strict five-second wins.
- Reading the saved sixty-second JSON confirms 309542 reported states and a
  witness of length 100004 with exactly five runs:
  `10^100000, 12, 14, 15, 2`. The parent investigation checked the branch's
  fourteen-place model: transition 10 (`transc_da`) consumes `ma_cap` (place 11),
  produces `ma` (place 6), and has a `da` (place 2) self-loop. Thus this witness
  contains a concrete long repeated block, not merely a suspected large search.
- `results/linux-application-gaps-v2` separately records checked sixty-second
  native-focused and native-symbolic successes near 0.56 seconds for this
  property. Those measurements use the older Linux binary and do not establish
  a threshold for the newer local binary.

## Mechanism suggested by the implementation

`src/original.rs` starts geometric scheduling with approximately
`remaining / (2 * branches)` and doubles the branch allocation each pass.
Every retry starts a fresh branch search. With twelve branches and five seconds,
the nominal first two allocations are about 0.208 and 0.417 seconds. If all nine
unresolved branches consume their allocations, these two passes require about
5.625 seconds before overhead, preventing a third pass.

`causal_portfolio` in `src/main.rs` gives local closure five percent of its
remaining budget (capped at 100 ms), then focused relaxed search sixty percent
of what remains. `focused_with_fallback` in `src/relaxed.rs` further splits that
phase: one third for helpful-action search and the remaining time for a fresh
unrestricted search. Consequently even the second geometric pass may provide
less than 0.25 seconds to the whole focused phase and restart work inside that
phase. The older successful phase used approximately 0.397 seconds.

This explains a plausible allocation failure, but host, binary and profiling
differences prevent a causal timing conclusion. The saved current output lacks
pass history and phase budgets. More profiling is unnecessary to establish the
long repeated block; it would only test the allocation hypothesis.

## Minimal targeted experiment

Implement an optional **finite repeated-transition successor** in the positive
search. Retain every existing single-transition successor. For an ordinary
Petri-net transition with input vector `a`, effect `d` and current marking `m`,
`k >= 1` repetitions are executable exactly when `m >= a` and
`m + (k-1)d >= a`, componentwise: each intermediate marking is on the same
linear segment. Check arithmetic overflow and compute the resulting marking
`m + kd` exactly. Choose finite repetition counts from resource exhaustion or
target thresholds; never interpret these extra successors or heuristic failure
as an unreachability proof. The self-loop input must remain in the enabling
condition even though its effect is zero.

Preserve repetition counts in witness ancestry and expand them for the existing
original-net checker, or use an independently checked exact repeated-step
certificate. Include witness construction in the measured solver time. A fast
search followed by a large trace expansion must not silently escape the budget.

The smallest useful performance comparison is CircadianClock RC12 with and
without this option, using one frozen binary, the same host, strict five-second
outer deadline and identical limits. Retain original-net validation and all
censored rows. Record expanded states, generated repeated successors, selected
repetition counts and trace construction time. This tests the known block
directly. Small deterministic semantic checks should cover decreasing places,
self-loops, exact targets, and overflow before that experiment. Broader claims
require the registered benchmark set and separate held-out evaluation.

If allocation diagnosis is still wanted, add pass index, assigned branch
budget, actual phase budget and phase duration to a separate profiled run of
the current frozen control and geometric configurations. Do not substitute
that diagnostic run into strict unprofiled timing results.
