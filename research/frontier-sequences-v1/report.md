# Independent checking of learned execution frontiers

The Python checker independently reconstructs all 368 logged count-bounded
execution graphs, totaling 130,940 states, and verifies every frontier exactly.
It checks the candidate state equation, confirms that no explored state reaches
the target, enumerates all enabled transitions, and compares the resulting
frontier and cumulative state counts with the Rust diagnostics. All five bounded
checker processes pass; no negative property verdict follows from this result.

| Branch | Checked cuts | Reconstructed states | General disjunctions |
|---|---:|---:|---:|
| DoubleExponent003 RC02/0 | 67 | 34,656 | 54 |
| DoubleExponent003 RC02/1 | 49 | 21,846 | 41 |
| DoubleExponent003 RC07/0 | 124 | 73,962 | 108 |
| DoubleExponent003 RC07/1 | 0 | 0 | 0 |
| TokenRing015 RC12/0 | 128 | 476 | 0 |

The DoubleExponent failures are not just one repeatedly incremented lower bound:
most cuts are disjunctions involving several transitions, often mixing positive
count bounds with previously unused transitions. TokenRing instead generates 128
all-zero frontier cuts from very small graphs. These observations argue against
assuming that a larger attempt cap or one scalar acceleration will fix both.

A proposed next experiment is to expand the permitted counts at an exhausted
frontier before querying the integer planner again. Completed exploration with
larger bounds can find a witness or exclude a larger componentwise-bounded set of
count vectors. The same first-exit proof applies to arbitrary nonnegative bounds;
the larger bounds need not themselves satisfy the state equation. However, a new
frontier inequality need not logically imply the old inequality outside those
bounded sets. Do not claim such implication or remove existing learned constraints
on that basis. Interrupted expanded exploration must never justify a cut.

This expansion is only a proposal and has no measured benefit yet. A bounded,
separately registered ablation would need to measure integer-query cost, state
exploration cost, and coverage against the frozen DFS planner. Relevant prior art
remains count-solution realization and increment refinement; no novelty claim.

The profiled binary adds VASS_FRONTIER_PROFILE logging to the DFS implementation;
normal benchmark binaries remain frozen. Each diagnostic uses five seconds internal
and seven seconds external time, followed by independent checks capped at sixty
seconds and sampled 2 GiB. The diagnostics are excluded from benchmark tables.

Evidence: plan.json, runs.jsonl, check-plan.json, checks.jsonl and audit.json.
Checker source: ../check-frontier-sequence-v1.py; collection source:
../probe-frontier-sequences-v1.py. Every source, input, executable and log is hashed.
