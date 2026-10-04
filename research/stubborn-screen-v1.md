# Stubborn reduction screen

The complete local screen has 208 rows: 104 properties, two methods, one
repetition, five seconds and 2 GiB. Baseline `portfolio-focused` solves 42;
`portfolio-stubborn` solves 40. Both refute 16; positive witnesses account for
26 and 24 respectively. All 82 definitive answers pass independent original
PNML/XML checking. No disagreements, validation failures or memory-limit events
were reported. All 126 unresolved rows hit the strict outer deadline.

There is one gain and three losses; their identities are retained in
`stubborn-screen-v1-analysis.json`. The 39 commonly solved cases have median
candidate/baseline wall ratio 1.00066, conditional on both solving. A single
local repetition establishes neither stable coverage nor a speedup.

By track, baseline/candidate solve 27/26 of 50 MCC properties, 15/14 of 44
FastForward properties, and 0/0 of 10 Boolean properties. All 104 remain in the
denominator. There are no exact canonical-branch hash duplicate groups; semantic
independence is not established. The full parent denominator remains 620.
Reserved evaluation families remain untouched.

`audit-stubborn-screen-v1.py` checks the full matrix, all definitive native
checks, frozen binary/source/runner identities, command configurations and
validation/resource limits. Its report includes family and selection-category
coverage. FastForward family labels use the original instance basename.

The one gain triggers registration of the full 104-property, three-repetition
comparison in `stubborn-repeat-v1-plan.json` under the existing protocol.
It is registered but not launched. First, the diagnostic plan retains all 13
previously selected cases and adds the three screen gain/loss cases not already
selected, totaling 16 properties and 32 rows. Diagnostics capture profiles
separately and allow two seconds of outer grace solely to collect counters;
their timings must not replace strict-screen timings.

The next implementation proposal is documented in
`target-directed-stubborn-review.md`. It remains unimplemented. The current
screen supplies no basis to promote the conservative reduction to the default.

All 29 FastForward positive rows additionally passed independent replay on the
original LoLA models and formulas. Evidence: `results/stubborn-screen-v1-lola-replay-v2`.
The first replay attempt is preserved with 29 metadata errors: the mixed manifest
lacks the original acquisition metadata. The wrapper now accepts an explicit
original source corpus, checks matching property identities, source hashes,
resolved inputs and ordered canonical branches, then uses the unchanged source
checker. Five identity regression tests pass. No measured answers were changed.
