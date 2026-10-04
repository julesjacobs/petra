# Sparse/focused application diagnostic

The four-property Linux diagnostic does not establish a stable coverage gain.
Across two repetitions at five seconds, neither native variant solved a query
in both runs; VerifyPN solved all four in both runs. The compact predecessor
had two memory-limit failures; both new variants had none. Focused search
proved CANConstruction once, with an independently checked negative proof.
The other native rows were unknown. Full rows, counters, environment and
runner snapshots are preserved in `results/linux-focused-diagnostic-v1`.

This compares the earlier frozen `linux-solver-raw-negative-structural-v1`
against `linux-solver-ordinary-focused-v1`, running both portfolio-local and
portfolio-focused. All use original PNML/XML, CPU 8, enforced 2 GiB,
user-space instruction counters, two repetitions and shuffled method order.
No definitive disagreement occurred. These are previously selected difficult
development cases, not a full-corpus experiment. Earlier diagnostic outcomes
were variable; preserve them instead of replacing them with this run.

An instrumented Mac run of the same new source, recorded separately in
`results/ordinary-phase-profile-v2`, gives a useful mechanism diagnostic:
focused search reduced DLC exploration from 58,343 to 344 stored states and
found a 632-state JoinFree witness. The latter was not independently checked
by Python in that instrumented run. AutoFlight remained unknown, and no Mac
run exceeded the sampled 2 GiB bound. Those exploratory results did not
translate to a stable original-input Linux solve under the five-second budget.
They must not be reported as a competitive speedup.
