# Combined portfolio: audited original-input Linux comparison

The combined native solver solves 135 of 176 properties, compared with 129 for
unrestricted VerifyPN, 97 for the qualified SMPT MCC portable configuration, and
128 for the frozen existing solver. It has no solved-set losses against any of
those three configurations in this run.

| Method | Reachable | Unreachable | Solved | Unknown |
|---|---:|---:|---:|---:|
| Native combined portfolio | 89 | 46 | 135 | 41 |
| Native count portfolio | 89 | 45 | 134 | 42 |
| Native walk portfolio | 88 | 45 | 133 | 43 |
| Frozen existing solver | 83 | 45 | 128 | 48 |
| VerifyPN unrestricted defaults | 83 | 46 | 129 | 47 |
| SMPT MCC portable | 52 | 45 | 97 | 79 |

All 1,056 rows were collected and pass the artifact audit, with zero audit issues,
invalid answers, or answer disagreements. Native definitive answers were independently
checked against original PNML/XML during execution; external answers remain
tool-reported. Forty-one properties remain unresolved by every configuration.

The cohort has 175 distinct ordered-branch representatives. The duplicate pair,
DNAwalker-PT-09ringLR RC00/RC07, is unknown for every method; deduplication therefore
leaves all solved counts unchanged and reduces each unknown count by one. This
exact-input relation does not establish independence between different queries.

The combined solver adds CloudReconfiguration-PT-311 RC06 over the count portfolio,
using independently checked reduction wrappers and finite-closure proofs. It also
retains RefineWMG-PT-100101 RC11 over the walk portfolio. Against the frozen existing
solver it gains those two properties and five RERS properties. Against VerifyPN it
gains the five RERS properties and DNAwalker-PT-18lozangeBlock RC01. Against SMPT it
gains 38 properties. Full paired lists are in summary.json.

The frozen plan uses five seconds per original-property invocation, CPU 8 affinity,
enforced 2 GiB memory, and separate bounded independent validation. This is a single
development repeat on one Linux host. It demonstrates the reported coverage at
this budget; it does not establish stable speed, general superiority, held-out
generalization, algorithmic novelty or publication readiness. The experimental
frontier count planner is not part of this combined binary.

Six audit warnings concern three timed-out SMPT invocations: RERS17pb114-PT-5 RC09,
RERS17pb114-PT-5 RC00, and RERS17pb114-PT-9 RC06. Their perf export was interrupted,
leaving missing or invalid instructions, cycles and task-clock values. Raw partial
artifacts are retained, no counters are imputed, and the unknown rows remain in
the coverage denominator. These warnings do not invalidate the coverage results.

Collection: 4,809 files in a 2,162,687-byte archive. Archive SHA256:
5a794950fd9c53ed16e96e0a1b73ee30e8ff645b2501b0e99d458123e5044cca.
Plan SHA256: 14ba740088129f3cd0b6d8f2e28c6dfb835ca03a29a409f0b51bb32b26b97978.
Evidence: collection.json, audit.json, audit.md, summary.json and frozen raw output
in results/linux-portfolio-reduced-v1. The exact remote process terminated with
exit code zero at 2026-09-28T15:24:05.634939Z; do not restart it.

Next: freeze a repeated five-/thirty-second matched comparison of the combined
solver, frozen existing solver, VerifyPN and SMPT using the draft in
../repeated-comparison-protocol-v1.md. Reserved evaluation families remain untouched.
