# Next benchmark and design track

**Prioritize checked raw-SER negative proofs with adaptive control projection. Finish the running ordinary-net ladder before choosing another application expansion.** The existing pairlocked ring cases expose a concrete proof-search gap, while simply increasing several MCC parameters mostly increases input representation size. This recommendation is a proposal; no new solver measurement was performed.

## What the present evidence measures

| Track | Observed evidence | Interpretation |
|---|---|---|
| Application expansion, 192 properties | Audited local control 189, buffer 191; historical Linux comparison has zero queries unresolved by every configuration | Useful regression set; mostly saturated at five seconds |
| FMS ladder, 11 new instances / 176 slots | Every instance has the same 22 places and 20 transitions; PNML is 16,347–16,402 bytes | Clean numeric-scaling opportunity, pending the running comparison |
| SharedMemory ladder | 2,651→40,601 places, 5,050→80,200 transitions; PNML 4.1→66.4 MB | Structural and input-size scaling are confounded |
| TokenRing ladder | 8,421→65,641 transitions; PNML 6.2→48.9 MB for sizes 20→40; size 50 fails collection cap | Keep all 64 slots, including 16 unavailable; collection failure is not reachability hardness |
| Historical 300-second survivors | Seven of eight unresolved by all configurations; 20 memory-limit rows | Strong evidence of configuration failure, but missing phase timings prevent attributing it entirely to search |
| Raw SER component-game portfolio | Six positives and four negatives checked in both repetitions; pairlocked sizes 4 and 5 unresolved | A specific remaining negative-proof mechanism, with a working size-3 bridge |

For the 381 validated rows in the local 192-property buffer comparison, median Rust parse time is approximately 0.6 ms; maximum is 0.134 s. Parsing therefore does not explain most of that cohort's observed work. This is conditional on rows with saved timing: three outer-timeout rows lack validated parse timing and must not be assigned zero parsing cost.

FMS is stronger than a name-based size argument: reading branch 0 for all 11 collected instances confirms identical place lists and transition arcs. Only three initial coordinates increase with the parameter (20 through 50,000); resource coordinates remain 3, 1 and 2. The supplied generated properties still vary across instances, so the 176-query cohort is not a fixed-property scaling experiment. Keep per-property results and, if needed later, preregister a separate common-property numeric ladder on these same development nets.

## Concrete raw-SER gap

The current `raw_negative::discover` tries an empty control projection, then one structural projection containing every eligible nonresponse/noncredit/nonsource place. It spends one eighth of its discovery allowance on the coarse attempt. There is no sequence of intermediate projections. Component transfers already use an AND/OR greatest fixed point, so repeating the previous greedy-to-game change is unnecessary.

The completed before/after portfolio comparison retains all 12 original diverse sources and 48 rows. `write_skew_n3_pairlocked` now has checked negative answers; `write_skew_n4_pairlocked` and `write_skew_n5_pairlocked` remain unknown in both repetitions. Their recorded input dimensions are:

| Case | Places | Transitions | Serial automaton states | Original exported JSON |
|---|---:|---:|---:|---:|
| pairlocked n3 | 140 | 3,852 | 64 | 1.06 MB |
| pairlocked n4 | 376 | 25,615 | 256 | 7.04 MB |
| pairlocked n5 | 1,198 | 153,618 | 1,024 | 42.37 MB |

Schema validation finishes before the reported solver-stage deadline. That establishes availability and a solver-stage failure, but Rust reparsing and internal preparation are not separately timed. Prior diagnostics explicitly record discovery-work exhaustion. Existing structural analysis finds only 7/15/31 reachable serial states for n3/n4/n5, despite the larger declared automata. This motivates separating serial-schema discovery, projected-control expansion, component-transfer solving and checking costs before changing the algorithm.

**Proposed general improvement:** refine the control projection from failed closure obligations, adding omitted enabling coordinates that distinguish a spurious abstract transition. Use original incidence only; maintain the existing universally checked transition-closure and completed-response inclusion obligations. Every successful certificate must independently check against the original query. An unsuccessful projection, exhausted refinement budget or schema search returns unknown. Intermediate finite projections could avoid enumerating unbounded pending-request coordinates and full global products; this benefit is unmeasured. Missing serial schemas are a separate failure cause and must not automatically trigger control refinement.

The publication value would be a precise certificate theorem and a general discovery improvement for raw automaton-Parikh exclusion targets, supported by an ablation from empty/structural projection to adaptive projection. Novelty and efficacy remain unestablished. Merely raising limits or adding program-name cases would not establish that contribution.

## Reproducible next experiment without reserved families

1. Use all 12 sources in `benchmarks/diverse-ser-programs-v1/manifest.json` and all 16 in `benchmarks/diverse-ser-scaling-v1/manifest.json`. Report the cohorts separately and identify four exact source bridges; their union contains 24 source programs. Keep pairlocked n6's export timeout in the source denominator. Do not regenerate larger programs yet.
2. Requalify the fixed scaling ladder with the current component-game portfolio before declaring its validated epoch cases hard. Its preserved pilot used the older frozen solver, while the later portfolio already proves validated moduli 3, 5 and 9. The larger moduli's current difficulty is unknown. All larger unsafe variants were solved by the old positive method; more modulus growth alone is weak evidence of harder reasoning.
3. Diagnose n4/n5 with separate phase counters outside competitive timing. Then freeze an adaptive-projection candidate and run a matched full-cohort ablation, including unsafe counterparts, under identical budgets. Preserve all query bytes, normalization identities, failures and independent certificate results. The existing raw harness includes checking inside the deadline; keep that policy for a matched experiment or freeze a clearly separate policy for both sides.
4. For ordinary-net external validity, retain the complete 464-slot running ladder and the prior 620-query parent collection. Inspect FMS numeric scaling separately from expanding-net families. Requalify the existing 8 historical survivors with a current frozen candidate before enlarging outcome-selected filters. Report parent denominators and selected views separately.

No reserved family is needed for any of these steps. Preserve the 22-family reservation in `harder-application-selection-v2.md`; no reserved net, property, archive or solver result was read for this analysis.

## Measurement and claim boundary

Keep one original-input competitive deadline, plus separately reported export and certificate-check costs. Add diagnostic phase evidence that survives a solver timeout; a missing final JSON currently erases parse/solve attribution. Successful-only parse statistics cannot classify failed queries. Use input bytes, dimensions, target branches, proof/game nodes and peak memory alongside wall time and instructions. Compare whole-query outcomes, not a union of isolated engines' best results.

Ordinary SMPT/VerifyPN input does not directly express the raw automaton-Parikh exclusion contract. A raw superiority claim needs a semantically matched baseline, such as the original complete SER workflow with all export/complement failures retained, or another explicitly equivalent implementation. The existing `raw-z3` is a project baseline, not SMPT. Independently checking the exported query still does not mechanically establish source-to-net correctness; source expectations remain separate evidence.

Local read-only evidence: `buffer-agglomeration-application-v1-verification.json`, `application-followups-v1-report.md`, `linux-hard-survivors-v1-verification.md`, `raw-component-game-portfolio-v1-analysis.json`, `raw-diverse-scaling-pilot-v1-analysis.json`, `raw-negative-choice-progress.md`, `raw-schemas-discovery.md`, the two raw collection manifests, the parameter-ladder manifest, and current `src/raw_negative.rs`. No imports, builds, solver runs, remote calls or transfers were performed. The running Linux experiment was not inspected or disturbed.

Reproduce the quantitative claims with `python3 research/audit-benchmark-hardness-next-track.py`. Its [evidence JSON](benchmark-hardness-next-track-evidence.json) records the read source hashes, FMS structural equality and varying initial coordinates, conditional parse statistics, exact source bridges, and pairlocked result rows. It records large PNML sizes and manifest identities without claiming to rehash those files.
