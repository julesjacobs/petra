# Stubborn reduction review

Coordinator review against `solver-counts-master-v1` and the preservation note:

- Opt-in dispatch shares capacity discovery, relevance, causal/local phases and
  time allocation with the existing focused portfolio. Symbolic remains unchanged.
- Sparse closure includes weighted necessary enablers and symmetric disabling
  dependencies, including readers. Visibility uses all target-support places.
- Freshness uses the pre-expansion seen set; fixed discovery depth, periodic
  full expansion and checked depth addition match the preservation argument.
- Ten private adversarial tests and direct unrestricted differential testing
  cover the principal obligations. Public variants are included in integration
  tests; original-input CLI capacity/relevance checks passed.

An intermediate implementation eagerly enumerated all enabled transitions even
in the original helpful-only phase. This would perturb the baseline. The agent
restored lazy iteration for both POR-off and helpful-only search; coordinator
source inspection confirms the fix. Only POR-on unrestricted search materializes
the enabled list.

A subsequent diagnostic probe exposed four `relaxed-search` events for two
attempts, including two empty default events. The constructor used struct-update
syntax with `Diagnostics::default()` while Diagnostics implements Drop. Dropping
the temporary default value emits a spurious event. This is an instrumentation
bug, not a reachability-answer counterexample. Requested fix: construct a single
default object and assign the flags, then verify exactly one event per attempt.
Before-fix probes are preserved. The constructor fix is now applied; the CLI
regression and release probes verify one event per attempt. Final validation:
359 tests passed, one pre-existing ignored, Clippy/release/format passed. Agent
sessions 86592, 70197 and 39734 exited zero and the local window was released.
Coordinator read the final source and logs; no remaining review blocker found.

No measured POR advantage has been established. The benchmark runner merges
stderr into the answer file, so profiling must remain disabled there; separate
diagnostics must capture stderr independently.
