# Independent implementation and evidence review

This review inspected saved reports, audits, plans and source; it ran no solver measurements or builds and did not rerun the campaign summarizer. The final [report](../grouped-excess-repeat-20261004/REPORT.md) is consistent with its [summary](../grouped-excess-repeat-20261004/summary.json) on coverage, denominators, stable gains, costs and conditional timing ratios. Both saved full audits pass with the same plan hash and 736 rows each.

| Implementation | Soundness boundary | Supporting evidence |
|---|---|---|
| [Grouped excess](../../src/grouped_excess.rs) | The sum of token mass above group thresholds is bounded initially and preserved by every original enabled transition; the target exceeds that bound. | [Theory](../grouped-excess-2026-10-04/theory.md), [independent Python checker](../../scripts/grouped_excess_checker.py), [checker tests](../../scripts/test_grouped_excess_checker.py), [Rust tests](../../tests/grouped_excess.rs), [CLI tests](../../tests/grouped_excess_cli.rs). The earlier grouped-only full screen adds 13 canonical DNAwalker answers with zero losses; it uses a different candidate binary. |
| [Divided-marking witnesses](../../src/scaled.rs) | Divide the initial marking by a common factor, retain original arcs, search a correspondingly scaled target, repeat the discovered word, then replay the original net and full signed target. This supplies positive witnesses only. | [Design](../scaled-witnesses-20261004.md). The [third diagnostic](../coverage-third-20261004/RESULTS.md) checks 25/31 answers from `scaled-walk`, all RERS properties. Equality divisibility and signed inequality rounding are part of the construction. |
| [Portfolio scheduling](../../src/main.rs) | Divided-marking and ordinary guided walks run before reductions; definitive answers retain original-input checking. | The [integrated survivor screen](../coverage-final-screen-20261004/RESULTS.md) solves 26/31 in actual shared five-second invocations. Its solved set exactly equals the third diagnostic's union: 25 RERS properties plus ASLink-PT-05b RC05. |
| [Guided walks](../../src/walk.rs), [relaxed search](../../src/relaxed.rs), [model validation](../../src/model.rs) | Guard-threshold indexing, action indexes, acyclic count realization and a reusable membership bitmap change search/validation costs; they do not replace witness checking. | [Static integration review](integration-review.md), [model validation tests](../../tests/model_validation.rs), final frozen source snapshot and complete comparison. No isolated speed contribution is established for each optimization. |
| [Backward cover](../../src/backward_cover.rs) | Necessary target lower bounds and guarded predecessors produce an upward-closed inductive exclusion certificate, checked separately. | [Python checker](../../scripts/backward_cover_checker.py), [checker tests](../../scripts/test_backward_cover_checker.py), [Rust tests](../../tests/backward_cover.rs). The diagnostic obtains no additional coverage; it is not evidence for the final coverage gain. |

## Evidence stages remain distinct

| Stage | Scope | Checked coverage conclusion |
|---|---|---|
| First grouped-only full screen | 368 original properties / 366 ordered-branch representatives | Candidate 337/368, baseline 323/368; representative counts 335/366 and 322/366. Fourteen original-property gains and thirteen representative gains, zero losses. |
| [Direct search](../direct-search-20261004/RESULTS.md) | 31 survivors, two methods | Guided walk 14, relaxed search 9, union 17. Separate invocations do not establish a shared five-second portfolio. |
| [Second diagnostic](../coverage-second-20261004/RESULTS.md) | Same 31 survivors, three methods | Backward cover 0, divided-marking relaxed search 12, then-current portfolio 13; union 19. |
| [Third diagnostic](../coverage-third-20261004/RESULTS.md) | Same 31 survivors, three methods | Ordinary guided walk 14, divided-marking guided walk 25, then-current portfolio 15; union 26. Its comparison with the earlier direct-search binary is explicitly descriptive. |
| [Final integrated screen](../coverage-final-screen-20261004/RESULTS.md) | Same 31 survivors, one method | Final portfolio 26, five unknown. All 26 definitive answers independently checked. |
| [Final full comparison](../grouped-excess-repeat-20261004/REPORT.md) | Two complete repetitions, 1,472 invocations | Candidate 363/368 both; baseline 323/368 then 322/368. Forty original-property gains recur, with zero losses. Representative counts are 361/366 both versus 322/366 and 321/366; 39 representative gains recur. |

The final screen's earlier generated wording incorrectly described its single-method result as an unmeasured union. The current report corrects this: it is an integrated five-second invocation per query. Its single-method exclusivity column is vacuous but does not alter coverage counts.

## Reporting checks and limits

- The full comparison preserves the baseline's RERS17pb114-PT-9 RC07 variation: reachable in the first repetition, unknown after the outer timeout in the second. It does not rerun or discard that observation.
- The 1,371 definitive answers equal 686 plus 685 accepted rows across the two audits. Unknown, timeout and nonzero-exit rows remain in the denominator; overlapping failure flags are not added as disjoint outcomes.
- Candidate solver plus validation time is 705.837 seconds versus baseline 798.548 seconds, an 11.6% reduction. Candidate validation costs more. Solver PAR-2 is 0.561 versus 1.495 seconds.
- The common-solved view is conditional on both methods solving a query in both repetitions. Its baseline/candidate geometric ratios, 0.897 for solver time and 0.857 including validation, indicate candidate slowdowns of about 11.5% and 16.7%. The report correctly limits its speed claim.
- The frozen [expansion](../benchmark-expansion-2026-10-04/README.md) adds 192 properties from six unused development families, comprising 191 ordered-branch representatives with no earlier-cohort overlap. All new arcs have unit weights, and the baseline already solves 187/192; neither weighted-arc coverage nor uniform difficulty is established.
- Candidate binary SHA-256 is `0f591ec86df357cac0ce175d26a9a77d59a69cc4bc51ec9bfe82a6543971b22e`. Both full audits name plan SHA-256 `b06c10b3a5554eea96eea26a5baabc7b934e6e09e392897dd0cd9fc006bc55bc`.
- The report distinguishes the later supplied RC12 witness from candidate discovery. Independent replay of that supplied witness does not change the frozen candidate's five unknowns.
- This review does not independently rerun the reported 621 Rust tests or Clippy. The final report attributes those to the pre-freeze checks and accurately records the unavailable built-in review.
- Reserved families remain outside this evidence. The development campaign supports repeated checked coverage on these inputs; it establishes no novelty, held-out generalization or external-solver comparison.

No outstanding actionable consistency finding remains after the integrated-screen wording correction.
