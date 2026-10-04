# One completion equality

For nonnegative markings, requiring every completion coordinate to be zero is equivalent to requiring their sum to be zero. `RawQuery::net()` now uses one equality with coefficient 1 at each completion place, or no row if there are no completion places. The serialized raw queries, response language, and independent checker are unchanged.

This replaces place-count times completion-count dense coefficient storage with one place-length row. It also changes guided scoring: a combined deficit replaces separately scaled deficits. Predicate acceptance is equivalent, but search order is not assumed identical. The change is frozen separately from preparation reuse for that reason.

Reduction recognizes a zero-support equality when the bound is zero and all coefficients have the same weak sign. Over nonnegative markings, each coordinate with a nonzero coefficient must then be zero, so it has the same disposability permissions as separate zero equalities. Initial nonzero values, protected places, and other target constraints still restrict elimination. Mixed-sign equalities are excluded, and coefficient negation is unnecessary, including for `i64::MIN`.

The quotient retains exact active coordinates and the passive sum, which together determine the combined equality. Positive results still require original replay and independent raw nonmembership verification; no new negative result is accepted.

Verification: 212 Rust tests passed, with one pre-existing ignored test; all-target clippy passed. New tests compare all eight completion subsets on 27 markings each, including `u64::MAX`; compare combined and expanded constraints for weighted shared-sink rewrites and lifted witnesses; and reject mixed-sign equalities as evidence of zero support. The full-scan reduction oracle receives expanded individual zero rows and is compared with indexed reduction on 512 deterministic weighted cases.

Frozen source and binary: `results/solver-completion-sum-v1`. Experiment: `research/raw-completion-sum-plan.json`, all 18 selected sources, two repetitions, 10-second input-inclusive deadline, 2 GiB sampled RSS. Compare with `results/raw-stress-prepared-v1`. Timing remains exploratory on the shared Mac. Results must be complete before assessing coverage or speed.

## Completed result

All 36 rows completed. Coverage is unchanged: five verified positives in both repetitions, seven valid queries unresolved, six exports unavailable. Mean observed times on the five common positives are slightly lower (for example, 2.7758 to 2.6553 seconds on monitor_d5_c128); this small shared-host difference does not establish a robust speedup. monitor_d5_c512 changes from two timeouts to one memory-limit failure and one timeout. Preserve this regression: less setup storage does not bound subsequent search storage.

Exact comparison: `research/raw-completion-sum-comparison.json`. The change reduces target representation size by construction, but has not demonstrated additional solved queries. The next search optimization should address dense state storage and successor generation, with phase diagnostics to distinguish search cost from target preparation and checking.
