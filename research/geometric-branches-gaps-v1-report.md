# Geometric branch scheduling: initial diagnostic

The optional geometric restart schedule adds no solved cases on the three
outcome-selected application gaps at five seconds. All 12 factorial rows are
retained. Control and geometric solve 0/3; buffer and combined solve 2/3.
Both NoC properties have independently checked original-net witnesses with
buffer or combined. CircadianClock RC12 remains unknown in every configuration.
There is no evidence here to promote the schedule as a default.

The candidate passed 11 deterministic scheduler tests, five CLI test groups,
27 Python runner/validator tests, formatting and Clippy. The initial formatting
failure is preserved. The frozen binary, 166 source files (including patched
varisat), test logs and review are in results/solver-geometric-branches-v1.
The default path remains single-pass; zero/single-branch queries also retain
single-pass behavior when the new flag is supplied.

The diagnostic used one local repetition, the same frozen binary for all four
configurations, a strict five-second outer deadline, two million states and
sampled 2 GiB process-tree RSS monitoring. Validation was independently bounded
and excluded from solver timing. Profiling was off. These selected development
queries provide no held-out or competitor evidence, and no stable speed claim.

The evidence audit checked the complete matrix, registered file identities,
flag assignments, budgets and saved independent checks for all four definitive
rows. It reran neither solvers nor proof checkers. See
geometric-branches-gaps-v1-verification.json and the reproducible auditor
research/audit-geometric-branches-gaps-v1.py. The process session 57338 terminated
with exit code zero; local development is available. Linux session 10739 remains
live and must stay free of engineering and bulk transfers.
