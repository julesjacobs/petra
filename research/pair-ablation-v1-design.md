# Uniform-pair ablation

`--method pair` invokes the same discovery and checker as `--method phase-pair`,
with an empty landmark set. Consequently every execution remains in phase0;
phase1 is empty and has no reachable execution. The existing two-phase certificate
contract accepts this special case without a checker change. Both methods retain
the same safety discovery, target-necessity check, relation allocation cap, pair
addition cap, and deadline handling. Neither method can prove reachability.

The deterministic regression fixture has an unreachable target that uniform
closure cannot exclude but phase-partitioned closure can. Another target in the
same fixture is excluded by uniform closure and accepted by both certificate
checkers. This establishes a strict precision difference on that fixture only.

Full-cohort experiment: the existing656-slot ordinary development cohort, including
640imports and16unavailable slots; no reserved-family acquisition. Compare both
methods at5s per original property, separate60s validation,2GiB local sampled
limits, one repeat. Keep Unknowns, errors, duplicates and unavailable inputs.
This is a local mechanism qualification, not a competitive Linux timing result
or an integrated-portfolio result. Its frozen runner is phase-pair-v1; shared
scripts remain unchanged while the independent Linux comparison runs.
