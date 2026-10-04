# Target closure optimization diagnostics

All 38 planned rows completed for 19 queries. The old target-directed binary solved 7/19; the optimized binary solved 6/19, with five common solves. All 13 definitive answers passed independent original-PNML/XML checks. All three FastForward positives additionally passed original-LoLA replay. There were no solver errors, outer timeouts, memory-limit events, validation failures, answer disagreements or malformed profile lines.

The audit verifies both frozen binaries and source archives, the registered selection evidence, exact randomized execution order, complete matrix, runner snapshots, 54 original/canonical input files, commands, profile files, saved validation requests/responses, and limits. Both methods are `portfolio-target-stubborn`; only their frozen binaries differ.

## What the counters establish

The optimized executions recorded **20,495 early full expansions** and **10,712,144 repeated dependency-list scans avoided**. Every recorded all-enabled selection exited early. Phase-specific failure counts sum exactly to the recorded 37 selection-limit fallbacks: eight during direction-index construction and 29 during closure, with none during target evaluation or seeding. These counters conflate work exhaustion and deadline expiration.

Both configurations entered the unrestricted fallback on 17/19 queries, in 18 attempts. DLCflexbar 7b RC00 and 8b RC00 were solved in the preceding focused attempt. The optimized fallback expanded states on only 15 queries: both FunctionPointer cases entered the fallback but expanded zero states. Consequently, zero selection failures on those cases provide no evidence that their selection bottleneck was removed.

| FastForward query | Old fallback expansions | Optimized fallback expansions | Optimized chosen / enabled actions | Repeated lists avoided |
|---|---:|---:|---:|---:|
| lu_fig2 multi60 | 1,774 | 4,447 | 46,412 / 47,651 | 2,200,667 |
| Dekker multi25 | 2,527 | 8,238 | 81,821 / 82,097 | 2,055,897 |
| Dekker multi30 | 2,293 | 9,639 | 90,479 / 90,849 | 2,578,913 |

These three whole relaxed phases each lasted approximately 2.63 seconds in both configurations. The optimized runs expanded more fallback states and eliminated substantial redundant list work, while still choosing 97.4–99.7% of enabled actions. Focused-attempt work also differed, and fallback time is not measured separately. The table therefore supports an overhead mechanism, not a measured equal-work speedup.

Aggregate selection-limit fallbacks dropped from 81 to 37, but 54 old failures came from the two FunctionPointer cases whose optimized runs expanded nothing. On MCC queries, failures instead rose from 25 to 37 across different trajectories. All eight optimized direction-index failures were two each on DLCflexbar 7b RC05/RC07/RC14 and 8b RC03. DLCflexbar 7b RC07 accounts for 25 of the 29 optimized closure failures despite 1,543,431 avoided repeated lists. This remains a concrete closure-cost case for investigation.

## Outcomes and attribution

The optimized-only lu_fig2 multi60 witness came from later `guided::solve`. The old-only Dekker multi25 and multi30 witnesses came from later `reduced::solve`. None is a direct success of the changed closure procedure. Both versions solved AutoFlight 96b RC09 and CANConstruction 090 RC06 directly in the target fallback, with identical recorded fallback expansion/generated/chosen counts. AutoFlight 96b RC05 was solved in a later branch's focused attempt; an earlier branch had reached the fallback, so attributing that query's success to the fallback would be incorrect.

The strict screen's FunctionPointer multi35 gain did not repeat: both diagnostic configurations were unknown. The strict screen's lu_fig2 loss reversed in this diagnostic. Original strict-screen results remain unchanged.

This is an outcome-selected development diagnostic: one repetition, five-second internal budget, seven-second outer cap, two million states and 2 GiB sampled process-tree RSS. Parsing and preprocessing are timed; independent validation is separate. FunctionPointer parsing alone took 2.74–3.27 seconds, and the present profiles do not locate the optimized pre-expansion cost. Aggregate counters mix trajectories and branches. No stable coverage improvement, regression, superiority or publication-readiness claim follows. The registered full-denominator repetitions remain the appropriate coverage comparison; further FunctionPointer diagnosis needs setup/first-expansion instrumentation.

Evidence: `research/audit-target-closure-diagnostic-v1.py`, `research/target-closure-diagnostic-v1-{analysis.json,audit.log}`, the immutable diagnostic run, and `results/target-closure-diagnostic-v1-lola-replay/report.json`. Re-audit with `vendor/venv/bin/python research/audit-target-closure-diagnostic-v1.py`; the one-time `--replay` option refuses to overwrite existing replay evidence.
