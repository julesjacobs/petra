# Target-zero trap diagnostic

All **26 rows over 13 queries** completed. Each configuration solved six queries and left seven unknown. The same six gains and six losses from the strict screen recur; the additional `double_lock_p2, 2, multi100` query remains unknown in both configurations. All **12 definitive answers** passed independent original-PNML/XML checks and original-LoLA witness replay, with no source-mapping exceptions.

The enabled configuration completed **11 nonempty, initially empty trap reductions**. Independent fixed-point reconstruction from the original canonical inputs reproduced every trap size and projected place/transition count. This is a static structural check, separate from measured solver execution. No initially marked trap proof occurred.

| Query (control parameter, multi size) | Original places/transitions | Retained places/transitions | Enabled outcome |
|---|---:|---:|---|
| Boop (2, 40) | 330/7489 | 67/1793 | Gain |
| Dekker (2, 25) | 164/1345 | 75/481 | Gain |
| double_lock_p2 (2, 100) | 184/1833 | 128/1137 | Unknown in both |
| double_lock_p2 (2, 75) | 184/1833 | 135/1373 | Loss |
| double_lock_p3 (3, 100) | 306/3137 | 216/1857 | Gain |
| lu_fig2 (3, 25) | 178/1617 | 113/665 | Gain |
| Peterson (2, 75) | 284/1985 | 146/1505 | Gain |
| Peterson (2, 90) | 284/1985 | 143/1281 | Loss |
| pthread5 (3, 60) | 187/1893 | 128/1189 | Loss |
| pthread5 (3, 90) | 187/1893 | 120/913 | Loss |
| pthread5 (4, 75) | 187/1889 | 121/941 | Gain |
| FunctionPointer3 (3, 35) | 2826/8961 | Preparation deadline; original input | Loss |
| FunctionPointer3 (3, 40) | 2826/8961 | Preparation deadline; original input | Loss |

Successful preparation took 1.75–5.69 ms. Both FunctionPointer preparations exhausted their approximately 100 ms preparation budget and fell back without transforming the input. Parsing took 2.72–2.83 s on these cases. Their unrestricted relaxed fallback expanded 0 and 11 states with the flag, versus 31 and 58 without it. Preparation overhead is measured and could contribute to the losses, but these profiles do not isolate its causal effect. Four further losses occurred despite completed size reductions: smaller nets did not consistently improve the subsequent search trajectories.

The enabled-only Boop and Peterson75 solutions came from the **unrestricted relaxed fallback**, following the focused attempt inside the engine labelled `relaxed-focused`. Dekker, lu_fig2 and pthread5 (4,75) succeeded in `reduced::solve`; double_lock_p3 succeeded in `guided::solve`. Disabled-only solutions came from `guided::solve` on FunctionPointer35, double_lock_p2 and both pthread5 cases, unrestricted relaxed fallback on FunctionPointer40, and `backward::solve` on Peterson90. FunctionPointer35's winning phase differs from the strict screen, despite the same verdict.

The audit verifies frozen binary/source identity, unchanged inputs, the complete randomized matrix, commands, captured profiles, limits and saved validation responses. There were no malformed profiles, solver/validation failures, outer timeouts or memory-limit events. Every unknown exhausted its internal deadline.

These are outcome-selected, single-repetition diagnostics with a **5 s internal budget and 7 s outer cap**. Their timings and outcomes must remain separate from the strict 5 s screen. Aggregate search counts mix different nets, trajectories and early exits. They establish neither equal-work performance nor a stable speedup.

Decision: retain the flag as opt-in; no default promotion or full repetition is supported. Prioritize the pending 192-query application comparison.

Evidence: `research/target-zero-trap-diagnostic-v1-analysis.json`, `research/target-zero-trap-diagnostic-v1-audit.log`, and `results/target-zero-trap-diagnostic-v1-lola-replay/report.json`. Recheck saved evidence with `vendor/venv/bin/python research/audit-target-zero-trap-diagnostic-v1.py`; the original replay used `--replay`. No solver measurements were rerun during this audit.
