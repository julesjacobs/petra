# Direct sparse Farkas verification

`linear::verify_certificate` now checks the supplied `sparse-farkas-v1` proof
against original arcs without constructing the state-equation matrix.
Discovery, certificate syntax and `System::check` are unchanged.

For original incidence matrix C, place-row multipliers lambda and signed target
row multipliers mu give combined place coefficients w=lambda+sum(mu*a).
The matrix check is precisely w*C<=0 and sum(mu*b)-w*m0>0. The direct checker
accumulates w and the right-hand side with arbitrary-precision rationals, then
checks each original transition. Combined place coefficients may be negative.
Equality rows retain negative-then-positive order. Problem validation, strict
certificate fields/kind, valid increasing row indices and positive multipliers
remain mandatory.

Focused verification completed:

- `cargo test --locked --test direct_farkas --test linear --test capacity --test capacity_cli`
  passed all 26 tests (`research/direct-farkas-focused-tests.log`).
- The systematic differential test compares 28,200 certificates across 600
  signed/equality/weighted systems with the unchanged matrix checker. Additional
  cases cover fractional near misses, signed combined coefficients, empty place
  spaces, zero transitions, extreme integers and malformed proofs/problems.
- `cargo clippy --locked --all-targets -- -D warnings` passed
  (`research/direct-farkas-clippy.log`); existing vendored Varisat warnings remain.

- `cargo test --locked` passed all 318 tests with one pre-existing ignored test
  and zero failures (`research/direct-farkas-full-tests.log`).

All owned process handles are terminal: focused tests 68929, Clippy 87665, full
regressions 1691, each exit 0. The final workspace workload check found no running
solver/build processes. The local Cargo window is released to root. No release
build or benchmark was run for this task, and no performance claim is made.
Frozen capacity artifacts and remote files are untouched.
