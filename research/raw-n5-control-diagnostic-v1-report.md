# n5 regression: negative discovery stops at its work limit

The two-row diagnostic identifies the immediate cause. Compressed negative
discovery terminates with an explicit **work-limit** during game expansion,
after2.501s in that phase. The enclosing negative procedure returns after3.725s.
The frozen balanced scheduler then enters positive fallback; the worker ultimately
reports the solver-phase wall deadline. The negative procedure itself did not
run out of wall time.

| Evidence | Dense | Compressed |
|---|---:|---:|
| Completed serial schemas | 212 | 212 |
| Structural game status | Complete | Work limit |
| Game-phase observed seconds | 7.242 | 2.501 |
| Cumulative structural work at game stop | 3,955,429,533 | 5,467,181,266 |
| Discovered / expanded game nodes | 167,874 /167,874 | 140,591 /124,877 |
| Interned control markings | 2,315 | 2,315 |
| Game edges /OR targets | 485,184 /1,562,122 | 369,228 /1,065,978 |
| Final answer | Independently checked negative | Solver timeout |

Dense extraction produces37,024 certificate nodes, and negative discovery plus
Rust checking finishes in17.664s. The whole-query dense answer is independently
accepted in44.557s. Compressed emits no answer or proof. Both schema searches
finish their candidate queues with identical90,360,083 charged work; this is not
a completeness claim about the full automaton Parikh image.

The registered intern charge changed2d→8d. This diagnostic confirms that the
compressed configuration's work accounting prevents completion of the negative
game at the existing allowance. It does not quantify how much of the difference
is caused solely by that change, nor prove that increasing the allowance will
finish within wall or memory limits. Less completed work and different stage
endpoints prevent treating the observed phase times as a speedup measurement.

The frozen analyzer reads118 dense and93 compressed records, with no malformed,
truncated or censored phase spans. The negative work-limit record is complete.
Positive fallback lacks these phase events: its execution is inferred from the
frozen scheduler's unconditional Unknown branch, not a sampled positive-search
trace. Its internal progress and precise stop point remain unobserved. The
worker's final deadline cannot establish a second work-limit cause.

All23 recorded artifact hashes were rechecked. The original input, existing frozen
binaries, unchanged checker and balanced schedule were used at60s outer wall,
80% solver fraction, sampled2GiB,100M states/10B applicable work, one invocation
per configuration, with phase diagnostics enabled. Dense independent proof
acceptance is preserved. This is local cause attribution, not competitive timing.

Evidence: `raw-n5-control-diagnostic-v1-plan.json`,
`raw-n5-control-diagnostic-v1-analysis.json`,
`raw-n5-control-diagnostic-v1-verification.json`, and both result folders.
Session11724 exited0 and the audit passed. The local gate is released.
No builds, source edits, Linux contacts or broader diagnostics occurred.

Next implementation decision: reconcile work accounting across control storage
representations or explicitly register a revised allowance, retaining an external
wall/memory budget. Then rerun the n5 regression before promotion. The completed
diagnostic already identifies the immediate failure; no broader run was launched.
