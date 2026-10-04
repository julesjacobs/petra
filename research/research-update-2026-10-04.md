# Research assessment, 2026-10-04

The evidence now favors testing an established symbolic reachable-set engine
before adding more firing-count heuristics. This assessment adds completed
repeated-run evidence, certified structural bounds, and a tested rejection of
one concrete optimization. It establishes no new solver speedup.

## Repeated comparison recovered

Collected all 4,224 original-input runs from the completed six-block comparison
and verified all 17,887 collected files. Five block audits pass. The remaining
block rejects one SMPT answer emitted after a `BrokenPipeError`; the registered
summarizer correctly refuses to produce a complete audited summary. A separate
[conservative diagnostic](repeated-comparison-linux-v1/diagnostic-report.md)
excludes that answer and preserves the failed audit and raw results.

| Method | Solved in every 5-second repeat /175 | Solved in every 30-second repeat /175 |
|---|---:|---:|
| Combined native solver | 134 | 143 |
| Frozen existing solver | 128 | 137 |
| VerifyPN | 129 | 139 |
| SMPT | 88 | 115 |

The denominator is 175 distinct ordered-branch representatives, with all 176
original properties retained in the accompanying data. At five seconds the
candidate gains 5–6 properties over VerifyPN with no losses. At thirty seconds
it gains twelve and loses eight in every repeat. All eight losses are DNAwalker
ring properties. Coverage superiority on this cohort therefore does not mean
solved-set inclusion at larger budgets.

Twenty-four representatives remain unresolved by every method in every
thirty-second repeat: five DNAwalker lozenge and nineteen RERS properties.
Native answers were independently checked during the original runs; external
answers remain tool-reported. These are development results.

## Structural premise checked

The four original models involved above all have nonincreasing total token
count. [Checked certificates](survivor-bounds-v1/report.md) give uniform place
bounds 22, 101, 90 and 162. They are bounded nets, and none is 1-safe in its
initial marking. This corrects any intuition based on 1-safe model metadata.

These bounds limit consecutive repetitions of a fixed word with nonzero effect
to at most the corresponding bound. Zero-effect repetitions add no new
markings. This supports investigating compression of different reachable
markings; it does not exclude long paths or establish that symbolic search wins.

## One optimization tested and rejected for these traces

We proved that at an identical marking, a prefix using componentwise fewer
transition firings can replace a more expensive prefix while preserving sound
frontier cuts. A [1-safe family](count-dominance-v1/theory.md) shows a strict
separation: ordinary count-frontier refinement can continue forever, whereas
this dominance rule closes the finite graph immediately. This is a correctness
and separation result; novelty is unassessed.

The [mechanism diagnostic](count-dominance-v1/v2/result.json) replayed all 368
saved DoubleExponent/TokenRing frontiers. Their 130,940 prefixes already have
distinct markings within each count box. Dominance removes zero prefixes and
changes zero frontiers. All checks complete; ten tests pass normally and with
Python optimization, including malformed-certificate rejection. The synthetic
cycle improves from 101 nodes to two, but these research traces show no benefit.
Production integration is therefore unwarranted. Duplication across successive
count boxes was not measured.

## Next discriminator

Finish [ITS-Tools runtime qualification](its-qualification-v1/report.md), then
register a comparison on the full 176-property development cohort. Preserve
both native controls and VerifyPN. Diagnose the eight ring losses separately
from the 24 jointly unresolved representatives, without replacing the full
denominator with these selected cases. ITS acquisition and adapter tests are
complete; runtime qualification and a measured comparison remain pending.

If ITS adds checked coverage, isolate the responsible representation and closure
mechanism before attempting a custom symbolic engine. Retain the dominance
theorem and negative diagnostic, and stop that optimization unless a different
workload supplies evidence of comparable prefixes at the same marking.
