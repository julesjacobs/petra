# Automatic signed-threshold discovery: implementation qualified

The new opt-in `signed-threshold` method automatically grows unary/binary
threshold clauses from target and predecessor failure cubes. It uses deterministic
full-rescan Houdini elimination, restarting the full eligible pool after growth.
`signed-threshold-unary` is the same implementation restricted to unary clauses.
Each negative proof is rechecked against the original problem before emission.
The default portfolio and positive search are unchanged.

Tests demonstrate automatic numerical upper/lower relational proofs on a
weighted net with an unrelated unbounded source; the unary ablation cannot prove
the relational target. All produced answers on336small conservative-net queries
are checked against exhaustive reachability and by independent Rust/Python
checkers. A regression explicitly requires revival of clauses removed before
new supporting candidates arrive. Candidate caps, zero deadlines/work and
invalid arity cannot emit proof.

Final selected Rust validation:243tests passed (228library,4original CLI,
5supplied-threshold integration,6discovery integration). Formatting and Clippy
passed after removing a stale unused variable introduced by the sparse delta
refactor. Earlier logs retained. The initial filtered test command ran only
kernel tests, not discovery integration; the final unfiltered command covers
all listed tests. Existing vendored varisat warnings remain.

The new isolated24-file runner `results/runner-threshold-v1` supports the proof
kind through bounded original PNML/XML validation and reduction wrappers. Four
composition tests pass. Frozen historical runners v1/v2 and shared benchmark
scripts remain unchanged. See threshold-composition-v1/validation.json.

Release build/freeze session57621 exited0. Complete source, release binary,
checksums and validation logs are in `results/solver-signed-threshold-v1`.
Source bytes were stable through the build and independently rehashed by the
registered run setup. Final independent checking uses the isolated frozen runner.

Full screen session34053 is running:1312rows, all656slots/640imports/16unavailable,
binary versus unary,5s original-input solve,sampled2GiB,separate60s checking,
one local repeat. See signed-threshold-full-v1-plan.json and execution.json.
No coverage or performance conclusion until terminal and full artifact audit.
Do not run local builds/solvers/imports/exports while34053is active.

This is an incomplete general weighted-net invariant engine, not a complete
reachability procedure or established research contribution. Numeric logical
charges are not hardware instructions. Costs and applicability must be measured
on the full cohort and a harder frozen development extension. All22reserved
families remain untouched. The user's objective remains coverage and speed first.
