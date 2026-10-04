# First coverage improvement: grouped excess

The frozen `portfolio-excess` candidate solves **337/368 original properties**
at a strict five-second original-input deadline, versus **323/368** for the
frozen `portfolio-reduced` baseline. There are fourteen gained properties and
no losses. Every definitive answer from both methods passed bounded independent
Python verification against the original PNML/XML input.

| Cohort | Properties | Baseline solved | Candidate solved |
|---|---:|---:|---:|
| Existing development set | 176 | 136 | 150 |
| Six-family expansion | 192 | 187 | 187 |
| Combined | 368 | 323 | 337 |
| Combined ordered-branch representatives | 366 | 322 | 335 |

The improvement comes from all fourteen previously unresolved DNAwalker slots
(thirteen distinct ordered-branch representatives). Both DNAwalker instances
are now fully solved. The remaining 31 properties are 26 RERS, four ASLink, and
one Railroad. All remain in the denominator. Two canonical duplicate pairs are
reported separately; raw slot counts are not independent observations.

The [expansion](../benchmark-expansion-2026-10-04/README.md) was frozen before
acquisition and measurement. It adds ASLink, MAPK, HouseConstruction, Railroad,
NQueens and ClientsAndServers, with two instances each. All 192 original
properties import and independently match. All new arcs have unit weights; the
set adds large initial counters and model diversity, but only five unresolved
properties in this screen. The 22 reserved evaluation families remain untouched.

## Cost and scope

| All 368 slots | Baseline | Candidate |
|---|---:|---:|
| Solver wall time, summed | 316.004 s | 248.583 s |
| Independent validation, summed | 88.646 s | 85.729 s |
| Solver plus validation, summed | 404.650 s | 334.312 s |
| Mean solver PAR-2 | 1.485 s | 1.106 s |

PAR-2 charges every unresolved/failed invocation ten seconds. It is a
coverage-sensitive penalty metric, not a speedup on commonly solved queries.
Validator time is outside the five-second solver deadline and is reported
separately. Timeout and nonzero-exit flags overlap: candidate has 29 and 27,
baseline 42 and 27. No unsuccessful outcome is discarded.

This is one local arm64 Mac development screen, with sequential invocations and
sampled two-GiB limits. It establishes checked coverage in this experiment.
It does not establish stable speed, held-out generalization, or superiority to
external solvers. The diagnostic on the 32 DNAwalker slots is a separate
observation and is not pooled as a second repeat.

## Mechanism and reproduction

The [grouped excess invariant](../grouped-excess-2026-10-04/theory.md) bounds the
sum of token mass above group thresholds. Discovery proposes groups from unit
transfers; the certificate checker verifies induction over every original
weighted transition and excludes a signed target row with exact arithmetic.
The Python checker uses a separately implemented breakpoint calculation.

Candidate binary SHA-256:
`f5e26006c887e3af913754e184e50c5e0b78e153ca3527f3ddcd8458a8390b2c`.
Baseline binary SHA-256:
`19ef799d463625b00fb779f77951ef2178dcd72bf768c8999659f1bcc5edc949`.
Frozen plan SHA-256:
`768c6e3d87abce736923b4ce851a9d160df09ed23ed7c58eb025f3affce14dd9`.

The [protocol](protocol.json), [plan](plan.json), [full audit](full-audit.json),
terminal receipt and source snapshots retain the exact schedule, input hashes,
runner/checker hashes, raw answers and independent validation responses. The
full stage contains all 736 scheduled invocations and 660 accepted definitive
answers, with no disagreements. The frozen harness refuses overwrites; a fresh
campaign directory is required for new measurements.

The implementation passed 590 Rust tests and Clippy before freezing; five new
Python checker tests passed with and without Python optimization. Subsequent
solver changes are separate candidates and do not alter this evidence.
