# Removing implied potential goals

For a nonnegative marking, `x_p - x_q >= b` implies `x_p >= a` whenever `a <= b`. If both sufficient nonmembership goals were retained, the binary goal adds nothing to their union and can be removed. This optimization operates only on the bounded candidate set and preserves the union of its target predicates. It does not prove unreachability, and removing a heuristic search target can still affect practical performance.

The largest monitor diagnostic (`results/raw-profile-monitor-v1`) showed 12 attempts, each receiving roughly 0.58–0.99 seconds. Candidate construction and reduction together took about 6ms. Nine binary targets were dominated by three retained unary targets. Removing them gives the remaining searches longer allocations under the existing scheduler.

Seven targeted raw-potential tests and all-target clippy passed, following the compact variant's 217-test full suite. New tests verify target-union equivalence over nonnegative markings across 64 pairs of signed bounds; the existing exhaustive candidate comparison uses a separately expressed dominance filter. Optional `VASS_RAW_PROFILE` logs preparation and per-attempt events to stderr; ordinary timing runs leave it disabled.

Frozen source/binary: `results/solver-dominated-goals-v1`. The initial all-source repeated run independently verifies monitor_d5_c512 in 5.539/5.807 seconds, with 10,242-transition witnesses. However, replicas_n10_racy changes from two checked positives to two outer timeouts, so stable coverage remains 8/12 with a changed solved set. Exact results: `research/raw-dominated-comparison.json`. Do not count the union as a deployed nine-query solver.

## Checker bottleneck and matched rerun

All four compact/dominance replica runs emit identical 15-transition traces, found by Rust in approximately 0.81 seconds. The timeout occurs in `positive-verification`, not Rust search. The independent Python checker constructed a response-by-period matrix of Z3 terms, including zero coefficients. It now indexes nonzero terms by response coordinate while retaining every original response equality, every original component, and the requirement for Z3 UNSAT on each component. The solver timeout is set after formula construction from the remaining deadline.

The checker change passed the raw pipeline suite, including 64 comparisons against the former dense Z3 formulation with correlated periods, empty periods, explicit members, and nonmembers. Original replay, overflow rejection, and unknown handling remain checked. New all-source two-repetition runs use this same checker for both frozen solver variants, with the same input-inclusive 10-second/2GiB envelope. Plan: `research/raw-sparse-checker-plan.json`. Earlier timeout results remain intact and the new checker cost must be distinguished from solver improvements.

## Completed matched-checker result

Both 36-row runs completed with identical runner hashes, input hashes, and resource settings. Stable verified coverage rises from 8/12 to 9/12; no positive is lost. monitor_d5_c512 changes from two solver timeouts to checked witnesses in 5.776/5.651 seconds, at about164–165MiB sampled peak RSS. replicas_n10_racy verifies in 1.346/1.257 seconds before pruning and 1.342/1.253 seconds afterward. This confirms that its earlier apparent regression occurred in checking.

Three valid queries remain unresolved: counter_d31_s16_locked, replicas_n8_locked, and replicas_n10_locked. Six sources remain unavailable due to export timeouts. These are development results, not held-out evidence or a record against general Petri-net competitors. Complete comparison: `research/raw-sparse-checker-matched-comparison.json`; final report: `results/raw-stress-dominated-checker-v2/REPORT.md`.
