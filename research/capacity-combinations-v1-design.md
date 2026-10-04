# Combining targets for structural capacity refutations

Opt-in `--method capacity` discovers nonincreasing0/1place potentials using the
existing incidence-based single-input implications and exact weighted validation.
Discovery ignores model names and does not assume global boundedness or safety.
Other places may be unbounded. This mode does not change default portfolios.

New seed selection sorts nonempty target supports by size and takes one coordinate
from each row per round, up to64distinct places. Equalities may nominate negative
coordinates. This prevents a wide early row consuming the whole seed allowance.

After the existing single-row refutations, consider sums of two signed target
rows (both directions for equality). For combined coefficients a and bound b,
a checked potential with support S and initial mass M refutes the target when
all positive coefficients are in S and b>alpha*M, where
alpha=max(0,max(a)). Nonnegativity rows with weights alpha*1_S-a, plus the two
original target rows with weight1, yield an ordinary `sparse-farkas-v1` certificate.
The existing exact Rust verifier checks it against the original problem before
emission; the independent Python verifier needs no change. BigInt arithmetic
handles signed equalities and combined bounds outside i64.

Discovery receives at most half the branch budget, capped at500ms. Discovery and
pair combination each have a logical-work allowance of20*--max-states, saturating
on overflow. These counts are not instruction counts or runtime upper bounds.
Pair construction and support scans consume this allowance and check deadlines;
final proof verification has caller-enforced hard limits. Missing proposals,
exhaustion, or checker failure leave Unknown. This is incomplete discovery of
ordinary linear certificates, with no novelty claim or new proof rule.

Tests cover a first target with80positive coordinates that previously starved
a singleton row, the absence of a single-row proof, exact signed row numbering,
large combined bounds, independent Python checking and rejection when a weighted
transition invalidates a previously discovered potential.

Initial qualification: all eight native-walk Unknowns from the audited656-slot
Linux parent, same candidate capacity versus original walk portfolio,5s per
original property,2GiB local sampling, separate60s independent validation, one
repeat. Preserve all16rows and distinguish this selected development pilot from
full-cohort performance or Linux competition. Baseline controls remain frozen.
