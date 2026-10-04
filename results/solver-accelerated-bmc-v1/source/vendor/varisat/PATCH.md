# Varisat 0.2.2 interrupt patch

Upstream: https://crates.io/crates/varisat/0.2.2
Source archive: `varisat-0.2.2.crate`
SHA256: `ebe609851d1e9196674ac295f656bd8601200a1077343d22b345013497807caf`
License: upstream MIT OR Apache-2.0; both license files are retained.

The upstream crate is copied unchanged except for the four source files listed
in `interrupt.patch`. That file is the exact unified diff against the published
crate. Cargo pins version 0.2.2 and patches it to this directory.

`Solver::set_interrupt` installs a callback checked before each decision/propagation
iteration, after propagation, and before popping each propagation queue literal.
A true result records `SolverError::Interrupted`. The CDCL driver checks this
before using the propagation result, so partial propagation cannot lead to a SAT
model or UNSAT decision. Polling precedes queue removal, preserving queue state.
The wrapper discards every interrupted solver and independently verifies all
successful models and RUP proofs.

The hook is cooperative, not an operating-system hard deadline. A single input
clause load, watch-list construction, propagation of one literal's complete
binary and long watch lists, conflict analysis, clause-database maintenance, and
model reconstruction are unchecked segments. Their data size is bounded by the
wrapper's input/proof budget. No result after the deadline is accepted. Work
units count input literals, variables, proof bytes, interrupt polls, and RUP
checker operations; they are not hardware instructions or exact propagation
literal visits. The bounded proof writer also reports deadline/size failures;
upstream propagates these via `solver_error` at the next scheduling boundary.

Freeze artifacts must include this entire `vendor/varisat` directory together
with Cargo.toml and Cargo.lock. No changes to SAT heuristics, propagation rules,
clause learning, or proof production are made.
