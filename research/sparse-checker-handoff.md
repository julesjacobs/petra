# Scoped task: direct sparse Farkas certificate verification

Local capacity measurement19606 is confirmed terminal. Linux60460 remains live: no remote actions. Root authorizes portfolio_audit sole local Cargo/build/test window for this task; root will not start local measurement until the window is released.

Implement the equivalent direct checker in src/linear.rs::verify_certificate, preserving the sparse-farkas-v1 proof format and every current validation condition. Avoid constructing state_equation(p) solely to verify a supplied certificate. The existing System::check remains the independent reference for tests.

For a place-row multiplier lambda_i and signed target-row multipliers mu_j, accumulate rational combined place coefficients w_i=lambda_i+sum_j mu_j*a_ji. Accumulate rhs=sum_j mu_j*b_j-sum_i w_i*m0_i. Verify every original transition has w*post-w*pre<=0 and rhs>0. Target equality row order is negative then positive. All certificate multipliers must be positive, strictly increasing valid row indices. Combined place coefficients can be signed; do not require them nonnegative. Retain strict serde fields, kind checking, Problem::validate, BigInt/BigRational arithmetic. No arbitrary floating-point acceptance or truncation. Keep implementation short and idiomatic.

Meaningful validation: compare acceptance with state_equation(p).check for systematic small signed/equality/weighted nets and multipliers, including fractional multipliers, malformed indices/order/sign, empty proofs, huge arithmetic including i64::MIN. Check existing capacity/Farkas regressions, then full suite and clippy. Do not alter existing discovery/solver methods or weaken the reference checker. No performance claims or new benchmarks. Record completed commands/results in research/direct-farkas-checker.md and report all process handles terminal. Frozen results/solver-capacity-v1 must remain unchanged.

COMPLETED: local window released. All 318 Rust tests and Clippy passed; all handles terminal. Details: research/direct-farkas-checker.md. No release build or benchmark was run.
