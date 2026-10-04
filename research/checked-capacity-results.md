# Checked capacity preprocessing: measured diagnostic coverage

The complete same-binary ablation in `results/capacity-predicted-pilot-v1`
contains 56 rows: all 14 statically predicted properties, two configurations,
two repetitions, five seconds per original property, sampled 2 GiB. Parsing
and preprocessing are included. Each answer is independently checked in a
separate bounded worker against the original PNML/XML and canonical branches.

| Configuration | Stable solved | Never solved | Intermittent |
|---|---:|---:|---:|
| Capacity preprocessing disabled | 1 | 12 | 1 |
| Capacity preprocessing enabled | 14 | 0 | 0 |

The disabled configuration solves DLCflexbar8b RC06 in both repetitions and
AutoFlight96b RC12 in one repetition. Enabled preprocessing refutes every
property in both repetitions; all 44 branch proofs pass independent sparse
Farkas checking. There are no contradictory definitive answers or validation
failures. The enabled configuration gains 13 stable solves, including the two
previously jointly unresolved properties DLCflexbar8b RC11 and RC12.

These are outcome-selected development diagnostics, not a full-denominator
competitive comparison. Read-only source/result inspection overlapped the
local run. There is no isolated speedup claim. A full-family comparison and
eventually a full-corpus single-core Linux comparison remain necessary to
measure overhead and regressions.

The frozen binary is `results/solver-capacity-v1/vass-reach`, SHA-256
`872d86055df527a0ea6a2e20e6fd025a19d619f30dc6d939bc6915681f192902`.
The disabled configuration wraps that exact binary with
`--no-capacity-preprocessing`; wrapper startup is included. The source archive
includes `vendor/varisat`. Plans, audited matrices and additional identity
checks are in `research/capacity-predicted-pilot-v1-{plan,analysis,verification}.json`.

The preprocessing uses metadata only to propose 0/1 nonincreasing place
potentials. Weighted original arcs validate them; contradictions use the
existing sparse Farkas proof language. This improves state-equation proof
discovery. Separately, `research/cyclic-capacity-separation.md` establishes a
strict increase in the power of a fixed token-flow abstraction when supplied
with checked finite capacities. The new preprocessing does not yet supply
its discovered potentials to the token-flow engine.

## Complete application-family comparison

`results/capacity-family-pilot-v1` contains all 96 original properties from the three AutoFlight and three DLCflexbar instances: 192 rows, two configurations, one five-second repetition. Both configurations use the newer direct Farkas checker, frozen at `results/solver-capacity-direct-v1`; only the capacity flag differs. Full matrix and all native answers pass independent checking.

| Family | Properties | Disabled solved | Enabled solved |
|---|---:|---:|---:|
| AutoFlight | 48 | 40 | 41 |
| DLCflexbar | 48 | 22 | 33 |
| Total | 96 | 62 | 74 |

There are 13 gains and one loss, DLCflexbar7b RC00. Enabled preprocessing times out on that property in the initial run, while the disabled configuration finds a checked witness. The new positive gain DLCflexbar7b RC08 was outside the 14 predicted refutations. No definitive answers disagree. Read-only analysis and browser activity overlapped this local pass; use it as coverage/regression evidence, not an isolated timing claim.

The separate `results/capacity-regression-profile-v1` follow-up repeats the lost query three times per configuration, with phase profiling and bounded independent validation. All six runs find the same 344-state relaxed-focused witness. The original loss remains in the full-family result; the follow-up does not establish an unconditional regression. Confirm stability on isolated Linux before changing the scheduler in response to this case.
