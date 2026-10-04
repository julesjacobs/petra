# CloudReconfiguration negative-gap diagnosis

The diagnostic pipeline now establishes unreachability of the complete original
CloudReconfiguration-PT-311 RC06 property. For both canonical branches, an independent
Python checker retranslates the original PNML/XML, checks agreement with every
canonical branch, reconstructs each buffer/relevance reduction from its certificate,
and exhaustively verifies the reduced reachable-state closure. Artifact audit passes.
This is separate from production-portfolio performance and does not change defaults.

| Branch | Places after two buffer/relevance rounds | Transitions | Reachable states exhausted |
|---|---:|---:|---:|
| 0 | 87 | 456 | 101,476 |
| 1 | 84 | 453 | 74,840 |

Each original net has 2,585 places and 3,095 transitions. A first buffer/relevance
round leaves 146/521 and 143/517 places/transitions. The second round eliminates
another 59 places in each branch. The diagnostic allocated three seconds per
branch; observed solver process walls were 0.676 and 0.316 seconds in one local
run. Independent closure checks took 9.115 and 6.679 seconds outside solver timing.
These measurements do not establish stable timing or a matched competitor gain.

An earlier reduced-input ablation compared BFS with the frozen count portfolio at
three seconds per branch. BFS exhausted both twice-reduced branches; the portfolio
returned unknown on both, reporting only one explored state. Thus useful explicit
search is available on these nets but is not reached effectively by this portfolio.
This does not isolate which preprocessing round is necessary: first-round-only BFS
has not yet been measured.

Exact duplicate-transition removal on the twice-reduced nets leaves 184/180 distinct
transitions, enabling three further buffer eliminations. The final sizes are 84/181
and 81/177; BFS exhausts 67,960/43,090 states. The portfolio also solves both of these
normalized diagnostic inputs. Those duplicate-removal experiments have independently
checked reduced-net answers, but their complete original-input reduction chains
were not certified here. The original-property proof above does not use deduplication.

VerifyPN's saved prior log reports reduction to 52 places/115 transitions and 3,410
explored states. Its final answer was previously only tool-reported; our diagnostic
now independently establishes the same negative property. Net sizes are not directly
identical representations: VerifyPN simplifies the query and handles it jointly.

Artifacts: `plan.json`, `results.json`, `dedup/`, `search/` and `closure/`.
The latter contains preserved source/binary/checker snapshots, reduction chains,
original input identities, bounded validation receipts and `audit.json`.
No change to the frozen Linux candidate currently running. This is a diagnosis and
verified use of established reductions/BFS, with no algorithmic novelty claim.

Next isolate first-round versus repeated reductions, then implement a general,
bounded composition of reductions and explicit closure proofs if the ablation
supports it. Preserve positive witness lifting, reject malformed chains and validate
small weighted/read-arc nets. Evaluate the resulting optional solver over complete
cohorts before altering defaults. Avoid attributing the gain to deduplication or
saturation alone without the corresponding ablation.
