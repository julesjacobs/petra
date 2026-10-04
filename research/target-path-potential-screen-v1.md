# Target-path potential factorial screen

The all-ones target-path potential flag increases solved coverage from **47/104 to 60/104** in this development screen. Combining it with target-zero trap reduction solves **62/104**. These are single-run observations; they justify further evaluation, not a stable speedup or default promotion.

| Track | Queries | Control | Trap | Potential | Combined |
|---|---:|---:|---:|---:|---:|
| FastForward random walk | 44 | 19 | 21 | 32 | 34 |
| MCC stress | 50 | 28 | 28 | 28 | 28 |
| Boolean consistency | 10 | 0 | 0 | 0 | 0 |
| Total | 104 | 47 | 49 | 60 | 62 |

Each configuration gives 16 unreachable answers. Every changed outcome is a FastForward positive. All **416 rows** are present, all **218 definitive rows** passed separate independent original-PNML/XML translation and witness/proof checks, and all **106 FastForward positive rows** additionally passed original-LoLA replay. Source mappings are exact, with no legacy mapping exceptions. There are no validation failures, definitive disagreements or memory-limit events. All 198 unknown rows hit the strict outer deadline and remain in the denominator.

| Candidate versus reference | Gains | Losses | Common solves |
|---|---:|---:|---:|
| Trap versus control | 7 | 5 | 42 |
| Potential versus control | 14 | 1 | 46 |
| Combined versus control | 18 | 3 | 44 |
| Combined versus trap | 13 | 0 | 49 |
| Combined versus potential | 4 | 2 | 58 |

Potential alone loses FunctionPointer3 (control 3, multi40) relative to control. Combined loses that query, FunctionPointer3 (3, multi35), and double_lock_p2 (2, multi75). Adding trap reduction to potential gains double_lock_p2 (2, multi90), double_lock_p3 (3, multi100), Peterson (2, multi100), and Szymanski (2, multi90), while losing FunctionPointer3 (3, multi35) and double_lock_p2 (2, multi75). Exact IDs, all gains/losses and checked engine labels are saved in the verification JSON. The aggregate potential increment is +13 with or without trap reduction; this does not imply identical per-query effects or establish absence of interaction.

FastForward family coverage is:

| Family | Queries | Control | Trap | Potential | Combined |
|---|---:|---:|---:|---:|---:|
| Boop | 2 | 0 | 1 | 2 | 2 |
| FunctionPointer3 | 9 | 4 | 2 | 3 | 2 |
| Dekker | 7 | 3 | 4 | 6 | 6 |
| double_lock_p1 | 3 | 1 | 1 | 3 | 3 |
| double_lock_p2 | 3 | 1 | 0 | 2 | 2 |
| double_lock_p3 | 2 | 0 | 2 | 1 | 2 |
| lu_fig2 | 5 | 4 | 5 | 5 | 5 |
| Peterson | 4 | 1 | 1 | 3 | 4 |
| pthread5 | 5 | 3 | 3 | 5 | 5 |
| Szymanski | 4 | 2 | 2 | 2 | 3 |

The motivating **double_lock_p2 (2, multi100)** remains unknown under control and trap alone. Potential solves it in 4.057 s through `guided`, and combined in 4.624 s through `reduced-guided`; both 100-transition witnesses replay on the original LoLA input. These timings describe this run only.

Negative branch proofs are identical in kind counts across configurations: 28 `sparse-farkas-v1` and two `causal-state-equation-v1` per configuration, covering 16 negative properties. No negative answer uses a new potential or trap wrapper. Profiling was disabled: positive engine labels preserve inner engine names and do not establish whether preparation actually transformed an individual query. In particular, `relaxed-focused` does not distinguish its focused attempt from its unrestricted fallback.

The audit verifies one frozen binary/source across all four labels, `portfolio-focused` throughout, exactly the registered 2×2 flags, randomized property order with rotating method order, all commands, 542 registered files, 18 runner snapshots, 152 archived source files, and 521 distinct input files (901,498,789 bytes). Limits were 5 s including startup, parsing and preprocessing, no outer grace, two million states and 2 GiB sampled macOS process-tree RSS. Validation used 60 s, 2 GiB, a 64 MiB response cap and 200 million DAG-check work units, outside solver timing; original-LoLA replay used 30 s and 2 GiB separately.

This outcome-selected set retains its parent denominator of **620**: MCC 368, FastForward 218, and Boolean consistency 34. It is neither held-out evaluation nor a new competitor comparison. There are no exact canonical-branch duplicate groups; semantic uniqueness is unproven. Repeat the complete matrix before claiming stable gains, then evaluate beyond this selected set. The combined configuration's extra solves must be weighed against its losses rather than promoting it from its total alone.

Evidence: `research/target-path-potential-screen-v1-{analysis,verification}.json`, `research/target-path-potential-screen-v1-audit.log`, and `results/target-path-potential-screen-v1-lola-replay/report.json`. Recheck saved evidence with `vendor/venv/bin/python research/audit-target-path-potential-screen-v1.py`. No solver measurements were rerun during this audit.
