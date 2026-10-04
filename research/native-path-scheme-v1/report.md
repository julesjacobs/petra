# Native fixed-path-scheme solving

Implemented `src/path_scheme.rs` and `examples/native_path_scheme.rs`. The example
runs entirely in Rust using existing exact integer arithmetic; it launches no SMT
process. Sparse word summaries now live in `src/summary.rs` and are shared with the
experimental BMC encoder. The separate dense compressed checker remains unchanged.

## Semantics

A scheme specifies an ordered list of original-transition words, each repeated a
positive number of times. For word i with hurdle h_i and effect d_i, introduce the
nonnegative integer x_i = n_i - 1. Its entry marking is

    m_i = m_0 + sum_{j<i} (x_j + 1) d_j.

The exact enabling constraint is

    sum_{j<i} x_j d_j - x_i max(-d_i, 0)
        >= h_i - m_0 - sum_{j<i} d_j.

Signed target inequalities/equalities apply to the final marking. Inequalities
become equalities using nonnegative slack variables. The existing arbitrary-
precision integer solver chooses counts. Every candidate then passes the dense
original-net compressed-witness checker. A construction entry cap, required
deadline, arithmetic row cap and node cap bound attempts. As with the other native
solvers, callers should retain the outer process resource guard.

Zero repetitions are represented by omitting that word from the scheme. The empty
scheme checks the initial marking. `Answer::Infeasible` excludes only the supplied
positive-repetition scheme. The example converts it to reachability `unknown`;
this module provides no global negative proof or automatic scheme search.

## Verification

- 10,368 assignments compared to direct original-transition replay: weighted arcs,
  read arcs, consumption/production, compound words, and signed equality/inequality
  targets.
- Native arithmetic finds a trillion-repetition compound-word witness; lowering
  the initial marking to disable the internal guard makes the scheme infeasible.
- Empty scheme, exhausted resources and malformed words checked.
- Fourteen fixed-scheme cases agree with real Z3; all five positive results pass
  the independent Python original-transition checker.
- Twelve existing integration tests and all 66 BMC semantic cases pass after the
  shared-summary move. Targeted Clippy passes; vendored varisat warnings remain.

These establish mechanism correctness on the checked scope. There is no benchmark
or novelty claim, no automatic selection of schemes, and no default portfolio
change. The next substantive task is choosing/refining useful schemes and measuring
that complete native method against the frozen controls and SMT references.
