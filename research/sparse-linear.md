# Sparse exact certificates from a numerical LP proposal

This is a reusable arithmetic component under development, not a novelty claim. It addresses the dense Fourier–Motzkin state-equation bottleneck observed on the new development corpus. `microlp` 0.6.0 (Apache-2.0, pure Rust) supplies numerical proposals; acceptance uses arbitrary-precision rational arithmetic.

For a system `x >= 0` and rows `A x >= b`, a certificate is a sparse vector of positive rational row multipliers `lambda` satisfying

```
lambda A <= 0       lambda b > 0.
```

Summing the original inequalities then contradicts `x >= 0`. Nonnegativity multipliers are implicit. The checker reconstructs the rows from the original net and target. It accepts no optimizer status as a proof, and never returns reachable from a feasible state equation.

Discovery maximizes `lambda b`, with `lambda >= 0`, `sum lambda = 1`, and `lambda A <= 0`. The normalization does not exclude any Farkas ray: every nonzero nonnegative ray can be normalized. Objective scaling and all floating-point rounding occur only in proposal generation. Bounded-denominator continued fractions propose exact multipliers at increasing denominator limits. Any candidate failing exact checking is discarded; failure to reconstruct yields unknown, even when the numerical optimum was positive.

The net encoding has one variable per transition and one row per nonnegative final place, followed by target rows. For each equality target, append its negation first, then the positive inequality. A place row is `C[p] x >= -m0[p]`; a target `a m >= b` gives `a C x >= b - a m0`. The same ordering is independently reconstructed by Python. Sparse incidence rows avoid the previous transition-count-squared collection of explicit nonnegativity rows and dense proof vectors.

The exported proof kind is `sparse-farkas-v1`; `multipliers` lists strictly increasing row indices paired with positive rational strings. The standalone Rust verifier and Python benchmark checker reject forged multipliers, wrong orientation, altered effects and altered initial markings. Unit tests also compare small bounded nets with exhaustive exploration and cover values beyond binary64's exact integer range.

The method is currently standalone (`--method sparse-state-equation`). It has not yet been included in the default portfolio. Five new Rust tests and the full 106-test Rust suite passed (one pre-existing artifact-dependent test ignored), as did Clippy with warnings denied and the two independent Python checker tests. A targeted pilot proved all seven selected development queries previously missed by the frozen portfolio, with all proofs checked independently. This is a tuning subset, not held-out evidence. The full 256-property development ablation is now running in `results/publication-sparse-linear`, using a frozen binary/source snapshot in `results/sparse-linear-v1`. Source changes do not modify the frozen executable under measurement. Exact verification establishes soundness of a returned certificate; it does not imply that numerical discovery is complete, optimal, or consistently fast.
