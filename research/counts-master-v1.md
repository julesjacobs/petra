# Counts-only numerical master: complete development comparison

All four registered runs completed in local session 59129, exit 0: 367 rows.
Manifest and binary identities match the plans. Complete matrices have no
contradictory answers or reported errors; all 84 definitive rows pass the
independent native-answer checks.

| Comparison | Budget | Before | After | Focused portfolio |
|---|---:|---:|---:|---:|
| Classical, 37 properties | 2 s | 20 | 20 | — |
| Hard development, 69 properties | 2 s | 0 | 0 | 2 |
| DLC7b RC01 probe | 20 s | unknown | unknown | reachable, 1.58 s |

The classical run also compares unchanged explicit finite-control engines across
the two frozen builds: both solve 20. Exact branch-file deduplication yields 34
classical representatives and 19 solves for every configuration. The hard view
has no matching branch-hash signatures. This is not semantic deduplication.

There is no demonstrated coverage or timing benefit from eliminating marking
variables. The classical conditional median after/before wall ratio is 1.0014
for the implicit engine (one repetition, including startup/parsing). This does
not establish equivalence or a precise performance estimate. Both implicit
engines hit the outer deadline in the 20-second probe; the new one emitted an
empty answer file, so its phase bottleneck cannot be diagnosed from that run.

DLC7b RC15 was separately run three times on each of three focused builds.
Relevant and counts builds solve 0/3; the lazy build solves 1/3. All other rows
time out. No build solves stably. This confirms sensitivity near the two-second
budget; it does not isolate an engine regression. The focused engine does not
invoke the new counts-only master.

The hard view is outcome-selected from 620 parent queries and the classical set
is a regression suite. These runs establish neither held-out improvement nor
competitive superiority. The separate 60-second Linux comparison remains live
and uses an earlier frozen candidate. Raw outputs and failures are retained.

Audit files: `counts-master-v1-verification.json` and
`counts-master-{dlc-probe,classic,hard,focused-repeat}-v1-analysis.json`.
Plans and the frozen candidate remain unchanged.

The next proposed intervention is conservative partial-order reduction in
witness search. A read-only review of completed older comparisons found that
checked capacity preprocessing resolved 14 of 27 remeasured members of the 34
VerifyPN-only selection gaps; all 13 still unresolved in that pass were reported
reachable by VerifyPN. Seven selected gaps were not remeasured there. Platforms
and configurations differ, so this is motivation for a new matched comparison,
not a current 20-case failure claim. A reachability-preservation argument must
handle unbounded invisible behavior, not only cycles in finite graphs.
