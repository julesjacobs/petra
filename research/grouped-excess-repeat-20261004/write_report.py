"""Produce the human-readable closeout from the two passed audits."""
import json
from pathlib import Path
F=Path(__file__).resolve().parent
ROOT=F.parents[1]
read=lambda p:json.loads(p.read_text())
summary=read(F/'summary.json');plan=read(F/'plan.json')
audits=[read(F/f'repeat{i}-audit.json') for i in (1,2)]
assert all(a['status']=='passed' for a in audits)
p=summary['reports']['pooled']['all_properties'];methods=p['methods']
lines=['# Solver and benchmark improvement at five seconds','',
'**The integrated candidate solves 363/368 original properties in both complete repetitions, versus 323 and 322 for the frozen baseline. There are 40 gains reproduced in both runs and zero losses.** All 1,371 definitive answers passed separate bounded independent checks against the original PNML/XML. All 1,472 scheduled invocations are retained.','',
'| Cohort | Slots | Baseline, repeats 1 / 2 | Candidate, repeats 1 / 2 |',
'|---|---:|---:|---:|']
for key,label in [('existing176','Existing development cohort'),('expansion192','Six-family expansion'),('pooled','Combined')]:
 v=summary['reports'][key]['all_properties'];m=v['methods']
 lines.append(f"| {label} | {v['denominator']} | {' / '.join(map(str,m['baseline']['solved_by_repeat']))} | {' / '.join(map(str,m['candidate']['solved_by_repeat']))} |")
v=summary['reports']['pooled']['representatives'];m=v['methods']
lines += [f"| Combined ordered-branch representatives | {v['denominator']} | {' / '.join(map(str,m['baseline']['solved_by_repeat']))} | {' / '.join(map(str,m['candidate']['solved_by_repeat']))} |",'',
'The candidate solves the same 363 slots in each run. Baseline RERS17pb114-PT-9 RC07 changes from reachable in 2.926 seconds to a 5.018-second outer timeout; this observation is retained. Paired gains are 40 and 41, with 40 common to both repeats. The representative view has 39 gains common to both repeats. Unknowns fall from 45/46 to five.','',
'## Where coverage improves','',
'| Family | Slots | Baseline, repeats 1 / 2 | Candidate, repeats 1 / 2 |',
'|---|---:|---:|---:|']
for key in sorted(k for k in audits[0]['reports'] if k.startswith('family:')):
 vs=[a['reports'][key]['views']['all_properties'] for a in audits]
 lines.append(f"| {key.removeprefix('family:')} | {vs[0]['denominator']} | {vs[0]['methods']['baseline']['solved']} / {vs[1]['methods']['baseline']['solved']} | {vs[0]['methods']['candidate']['solved']} / {vs[1]['methods']['candidate']['solved']} |")
lines += ['',
'The 40 repeated gains comprise fourteen DNAwalker properties, twenty-five RERS properties, and ASLink-PT-05b RC05. The gains are concentrated in these three families. The earlier grouped-only candidate solved 337/368 in its own screen; its binary and results are distinct and are not pooled into this comparison.','',
'## Implementation','',
'- [Grouped excess](../grouped-excess-2026-10-04/theory.md) proves negative answers by bounding the sum of token mass above group thresholds. Induction and target exclusion are checked exactly, with a separately implemented Python checker.',
'- [Divided-marking witnesses](../scaled-witnesses-20261004.md) search from a common divisor of the initial marking without changing any transition arcs. A positive word is repeated, expanded and replayed on the original net and full signed target. A failed reduced search never refutes the original problem.',
'- The portfolio runs divided-marking guided walks and ordinary guided walks before optional reductions, then divided-marking relaxed search and previous fallbacks. This preserves the original-net ASLink witness that reduction changed in an intermediate diagnostic.',
'- Guided walks skip enabledness-user scans when no guard threshold can change. Relaxed search retains exact enabled actions and indexes sources and target effects. Count realization uses topological blocks when its producer/consumer graph is acyclic. Input validation reuses a place-membership table, and large arithmetic construction is bounded before starting.',
'- `--method auto` now chooses `portfolio-excess` for ordinary input and preserves `raw-potential` for raw input. Prior named methods remain selectable. The measured configuration explicitly enables buffer agglomeration and uses two million states/firings.','',
'These are integrated changes. The selected diagnostics identify useful mechanisms but do not establish an isolated speed contribution for every implementation optimization.','',
'## Cost, including verification','',
'| Both repetitions, all slots | Baseline | Candidate |',
'|---|---:|---:|']
for label,key in [('Solver wall time, summed','solver_wall_total_seconds'),('Independent validation, summed','validation_wall_total_seconds'),('Solver plus validation, summed','end_to_end_wall_total_seconds'),('Mean solver PAR-2','solver_par2_mean_seconds')]:
 lines.append(f"| {label} | {methods['baseline'][key]:.3f} s | {methods['candidate'][key]:.3f} s |")
ratio=p['common_solved']['geometric_mean_baseline_over_candidate']
reduction=100*(1-methods['candidate']['end_to_end_wall_total_seconds']/methods['baseline']['end_to_end_wall_total_seconds'])
lines += ['',f'Total solver-plus-validation time decreases by {reduction:.1f}%, while validation cost increases because additional answers and longer expanded witnesses are checked. PAR-2 charges every unknown/failure ten seconds; it is a coverage-sensitive penalty, not common-case speed.', '',
f"On the 322 queries solved by both methods in both repetitions, the geometric mean baseline/candidate ratio is {ratio['solver']:.3f} for solver time and {ratio['solver_plus_validation']:.3f} including checking. Thus the candidate is about {100*(1/ratio['solver']-1):.1f}% slower on this selected solver-only view and {100*(1/ratio['solver_plus_validation']-1):.1f}% slower including checking. Broader coverage is the primary gain; this is not a uniform speedup.",'',
'## Benchmark improvement and limits','',
'The [192-property expansion](../benchmark-expansion-2026-10-04/README.md) adds ASLink, MAPK, HouseConstruction, Railroad, NQueens and ClientsAndServers, with two instances each. Selection was frozen before acquisition and solver outcomes. All original imports independently match; 191 ordered-branch representatives have no overlap with the earlier cohort. Combined reporting retains 368 slots and 366 representatives.', '',
'All new arcs have unit weights. The expansion adds model diversity and large initial counters, not weighted-arc coverage. It is mostly easy for the baseline: 187/192 were already solved. All 22 reserved evaluation families remain untouched. These are two local arm64 Mac development repetitions with sampled 2-GiB process-tree limits and no overlapping builds or solver measurements. They establish repeated checked coverage here, not held-out generalization, precise speed confidence intervals, novelty, or external-solver superiority.','',
'## Unresolved and unsuccessful experiments','',
'The same five properties remain unknown in both candidate repetitions:','',
'- RERS17pb114-PT-5 RC12',
'- ASLink-PT-05b RC06',
'- ASLink-PT-10b RC05',
'- ASLink-PT-10b RC07',
'- Railroad-PT-100 RC09','',
'Backward cover solved none of the 31 survivors in either of its two source versions and stays standalone. The earlier count-dominance experiment also had no benefit. A walk-heavy intermediate portfolio missed complementary relaxed-search witnesses; the next version still missed the ASLink witness after reduction. All diagnostic rows, failures, snapshots and audits remain available in the [first](../coverage-iteration-20261004/README.md), [direct-search](../direct-search-20261004/RESULTS.md), [second](../coverage-second-20261004/RESULTS.md), [third](../coverage-third-20261004/RESULTS.md), and [integrated survivor](../coverage-final-screen-20261004/RESULTS.md) records.','',
'The [Pro consultation](https://chatgpt.com/c/6ac195da-cc4c-83eb-a123-e76ea2d22af5), obtained with the [Pro skill](/Users/julesjacobs/.codex/skills/pro/SKILL.md), proposes combining different one-copy endpoints for RC12. Its [assessment](../pro-coverage-20261004/assessment.md) distinguishes supplied evidence from independently reproduced results. After the campaign finished, the supplied 5,192-transition RC12 witness and both component words passed [independent original-input replay](../pro-coverage-20261004/rc12-independent-replay-v1/result.json), in 3.912 seconds of checking. This confirms a reachable target, but the candidate did not discover it; it remains unknown in the measured score. Combining different endpoints is a separate possible follow-up.','',
'## Checks and reproduction','',
'621 Rust tests passed, two were ignored, and Clippy passed before the final freeze. Grouped-excess and backward-cover Python checker tests passed; optimized-mode checker checks are retained. [Static integration review](../final-review-20261004/integration-review.md) found no actionable issues. `codex review -` could not start because this directory is not a Git repository; its logs are retained and no clean built-in review is claimed. Witness replay is not internally interruptible at every step, so the outer deadline and late-answer rejection remain necessary.','',
'```sh',
'cargo build --release',
'./target/release/vass-reach --pnml model.pnml --xml properties.xml \\',
'  --property-id QUERY_ID --method portfolio-excess --seconds 5 \\',
'  --max-states 2000000 --buffer-agglomeration',
'```','',
f"Candidate binary SHA-256: `{plan['binaries']['candidate']['binary_sha256']}`.",
f"Baseline binary SHA-256: `{plan['binaries']['baseline']['binary_sha256']}`.",
f"Frozen plan SHA-256: `{summary['plan_sha256']}`.",'',
'The [protocol](protocol.json), [plan](plan.json), [first audit](repeat1-audit.json), [second audit](repeat2-audit.json), [summary](summary.json), terminal receipts and frozen source/binary snapshots contain exact commands, ordering, hashes, accepted answers, validator requests/responses and all failures. The harness refuses replacement measurements; use a fresh campaign directory for another version.','']
i=lines.index('## Benchmark improvement and limits')
failures=['## Retained unsuccessful outcomes','','| Repeat | Method | Unknown | Timeout flag | Nonzero exit flag |','|---|---|---:|---:|---:|']
for repeat,audit in enumerate(audits,1):
    for method in ['baseline','candidate']:
        v=audit['reports']['pooled']['views']['all_properties']['methods'][method]
        flags=v['failure_flags']
        failures.append(f"| {repeat} | {method} | {v['verdicts'].get('unknown',0)} | {flags.get('timeout',0)} | {flags.get('nonzero_exit',0)} |")
failures += ['','Timeout and nonzero-exit flags can describe the same invocation; they are not disjoint failure counts. Every such row remains unknown in the score. All accepted definitive rows have successful independent checks.','']
lines[i:i]=failures
(F/'REPORT.md').write_text('\n'.join(lines))
