# Current source footprint

Measured with cloc 2.08: `cloc --json --by-file src tests examples scripts`.
Source identities are pinned in files-sha256.json; per-file counts are in cloc.json.
Counts exclude blank and comment-only lines, vendored dependencies, build output,
benchmarks, and research scripts/reports. These are source-size measurements,
not complexity, runtime footprint, or a minimal implementation estimate.

| Scope | Files | Code lines |
|---|---:|---:|
| Rust src, including inline and source-tree unit tests | 70 | 29,686 |
| Rust integration tests | 52 | 11,809 |
| Rust examples | 11 | 556 |
| Python integration tests | 3 | 514 |
| Python scripts/frontends/checkers/runners | 125 | 15,869 |
| Shell scripts | 8 | 382 |

Rust src + integration tests + examples total 42,051 code lines. Source-tree
unit tests prevent treating the 29,686 src count as production-only code.
The experiment collection is broad: lib.rs exports many optional mechanisms;
these counts do not establish that the strongest measured portfolio needs all
of them. A future algorithm consolidation should preserve experimental artifacts
and test semantics while measuring a separately defined core.

## Constraint-solving dependencies

Cargo.toml pins embedded microlp 0.6.0 and patched varisat 0.2.2. src/linear.rs
uses microlp to propose numerical models and certificates, with exact arithmetic
checking at acceptance boundaries. src/control.rs also invokes microlp.
src/sat.rs embeds varisat. The native solver therefore does not need an external
SMT executable for these mechanisms; it still depends on general optimization
and Boolean reasoning libraries.

src/accelerated_bmc.rs is an optional QF_LIA encoder. The existence of that
encoder is distinct from the dependencies of the measured native portfolio.
SMT experiments and native fixed-word path-scheme implementations coexist; an
SMT-vs-native performance conclusion needs a matched measured comparison.
The original-input measurement track also includes a Python PNML/XML frontend;
a standalone Rust backend should not be described as an entirely Rust end-to-end
benchmark invocation.

The current architecture review remains in progress. This inventory makes no
claim of algorithmic novelty, solver completeness, or performance superiority.
