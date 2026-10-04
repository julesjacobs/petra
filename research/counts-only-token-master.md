# Eliminate final markings without changing the relaxation

Status: implemented and independently reviewed. 348 Rust tests passed (one
pre-existing ignored); final deadline changes were revalidated with 133 library
and 13 linear tests, Clippy and release build. Three release-generated answers
passed the independent Python checker normally and under `-O`. Frozen candidate:
`results/solver-counts-master-v1`. Performance measurement pending.

For the active edge set, write the marking equations as m = m0 + Delta*x.
The numerical master can use only nonnegative edge counts x. Retain each
marking-nonnegativity row Delta_p*x >= -m0_p. In every selected-coordinate,
target or cut row, replace occurrences of m by m0 + Delta*x. Mode-balance
rows are unchanged.

Store a nonnegative combination of original canonical rows for each reduced
row. A substituted positive coefficient a of m_p uses a times the negative
marking equation; a negative coefficient uses -a times the positive equation.
The marking-nonnegativity row itself uses the negative marking equation,
leaving coefficient -1 on m_p. This remaining nonpositive coefficient is valid
in the full Farkas contradiction because original variables are nonnegative.

Lift reduced Farkas multipliers through these combinations, merge canonical
indices and check the full original restricted master. Then price all implicit
columns as before. Reduced feasibility alone is used only for candidate models:
reconstruct all markings and check every full master row before separation or
original-transition witness realization. The external proof format and independent
checker need no change.

Rows that become 0 >= b with b <= 0 can be discarded for the current active set.
Rebuild their substitutions when new columns arrive: a discarded row can become
nontrivial. Retain a positive constant contradiction.

Preserve the previous objective sum(x) + sum(m). After substitution its edge
coefficient is 1 + sum_p Delta_p,e, up to the constant sum(m0). Coefficients may
be negative; retaining marking nonnegativity keeps the objective bounded below.
For example, consuming two tokens with one firing has coefficient -1: the old
objective prefers that firing, whereas minimizing edge counts alone would not.

Evaluate feasibility/model reconstruction, mixed-sign proof lifting, changing
active sets, negative objectives and deadlines before the full paired comparison.
Record numerical dimensions and phase outcomes. This is exact elimination of an
existing relaxation; no new expressiveness or performance gain is claimed.
