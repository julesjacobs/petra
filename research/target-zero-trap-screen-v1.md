# Target-zero trap screen

Both configurations solved **47/104**, with **six gains, six losses and 41 common solves**. Tied totals conceal substantial changes in which queries were solved. Both produced 31 reachable and 16 unreachable answers.

| Track | Queries | Disabled | Enabled |
|---|---:|---:|---:|
| MCC stress | 50 | 28 | 28 |
| FastForward | 44 | 19 | 19 |
| Boolean consistency | 10 | 0 | 0 |

All changed outcomes were FastForward positives. Names below retain their control parameter and `multi` size; exact query IDs and checked engines are in the verification JSON.

| Enabled-only solve | Disabled-only solve |
|---|---|
| Boop_simple, 2, multi40 | FunctionPointer3, 3, multi35 |
| Dekker, 2, multi25 | FunctionPointer3, 3, multi40 |
| double_lock_p3, 3, multi100 | double_lock_p2, 2, multi75 |
| lu_fig2, 3, multi25 | Peterson, 2, multi90 |
| Peterson, 2, multi75 | pthread5, 3, multi60 |
| pthread5, 4, multi75 | pthread5, 3, multi90 |

The enabled-only Boop and Peterson witnesses came from `relaxed-focused`; Dekker, lu_fig2 and pthread5 from `reduced-guided`; double_lock_p3 from `guided`. These engine labels identify the successful search, not whether target-zero reduction changed that query. Profiling was disabled, and positive witness lifting preserves the inner engine label. No checked negative answer used either new target-zero trap proof form: each configuration's negative branch proofs comprised 28 sparse-Farkas and two causal-state-equation proofs. Mechanism attribution therefore requires the registered diagnostics.

All **208 rows** completed. All **94 definitive rows** passed separate independent original-PNML/XML translation and witness/proof checks. All **38 FastForward positive rows** also passed original-LoLA replay, with exact source mappings and **no legacy mapping exceptions**. There were no validation failures, disagreements or memory-limit events. All 114 unknown rows hit the strict outer deadline and remain in the denominator. No duplicate groups were found using exact canonical branch hashes; this does not establish semantic uniqueness.

The audit verifies the same frozen binary/source for both labels, `portfolio-focused` for both, and `--target-zero-trap` on `after` alone. It also verifies all 541 preregistered files, 17 runner snapshots, 521 unique input files (901,498,789 bytes), the complete randomized matrix, exact commands, environment limits, and saved validation requests/responses. The runner snapshots are those of this experiment, including its new checker and flag support.

Limits were five seconds including startup/parsing/preprocessing, no outer grace, two million states and 2 GiB sampled macOS process-tree RSS. Independent validation used 60 seconds, 2 GiB, a 64 MiB response cap and 200 million DAG-check work units, outside solver timing. The conditional median enabled/disabled wall-time ratio was 0.99945 over the 41 common solves. It excludes unresolved queries and does not establish a speedup from one repetition.

This remains outcome-selected development evidence drawn from 620 parent queries: MCC 368, FastForward 218 and Boolean consistency 34. It is neither held-out evaluation nor a new comparison with external solvers. Decision: keep the flag opt-in, with no default promotion or full repetition yet. Prioritize the pending 192-query application comparison. The registered 26-row diagnostic covers all 12 changed queries plus an additional double-lock case; its timing will remain separate from this strict screen.

Evidence: `research/target-zero-trap-screen-v1-{analysis,verification}.json`, `results/target-zero-trap-screen-v1/{environment.json,runs.jsonl,runner-source}`, and `results/target-zero-trap-screen-v1-lola-replay/report.json`. Reproduce the audit with `vendor/venv/bin/python research/audit-target-zero-trap-screen-v1.py`. No solver measurements were rerun during this audit.
