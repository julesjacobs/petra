# Target-directed stubborn diagnostics

All36 planned rows completed for18 properties. Focused solved4/18 and target-directed5/18; all nine definitive answers passed independent original-input checks. No validation failures or non-JSON profile lines. Frozen binary, source, runner snapshots, complete matrix and51 original/canonical input files verified by audit-target-stubborn-diagnostic-v1.py.

The reduced fallback was reached on every target-directed query (19 attempts across18 queries). Across those distinct trajectories,32,915 expanded nodes produced27,183 reduced selections,5,556 all-enabled selections,174 work-limit fallbacks and two interrupted selections. Earlier interim commentary suggesting some cases did not reach the fallback was incorrect; the complete profiles establish that they did.

Two screen gains repeated and were solved directly by the target-directed search:

| Query | Target fallback expanded | Enabled transitions considered | Chosen transitions | Reduced selections |
|---|---:|---:|---:|---:|
| AutoFlight-PT-96b RC09 |1,224|344,069|5,686|1,221|
| CANConstruction-PT-090 RC06 |48|3,671|1,756|21|

Their focused counterparts remained unknown. This is concrete mechanism evidence for pruning; it does not establish a stable timing improvement.

FastForward behavior is less encouraging. FunctionPointer3 multi40 completed only11 fallback expansions, all hitting the selection work cap and choosing all enabled transitions. The lu_fig2 multi60 case selected17,077 of17,537 enabled transitions: little pruning. Its target run stayed unknown while the focused portfolio found a witness later in guided search. Dekker multi25 again appeared as a coverage gain, but its witness came from the later reduced::solve phase, not the target-directed search. These later-phase wins/losses cannot be attributed directly to stubborn-set pruning.

DLCflexbar8b RC00 was a diagnostic loss: target selection hit its work cap134 times among232 expansions; focused relaxed search found a witness. The other two strict-screen FastForward losses (FunctionPointer3 multi40 and Dekker multi30) were unknown in both diagnostic configurations. All original screen outcomes remain unchanged.

These are outcome-selected diagnostics:5second internal budget,7second outer cap to permit profiles,2GiB sampled RSS,2million states,one repetition. The extra grace and profiling make this a different experiment from the strict screen. Aggregate state/transition counts mix trajectories, so their ratio is not a state-space or throughput comparison on equal explored work.

Next: inspect exact direction-index and closure costs, especially work-cap fallback and low-pruning cases, before selecting a change. Full104×2×3 target-stubborn repeats are registered in target-stubborn-repeat-v1-plan.json and remain unlaunched. The separate conservative-stubborn repetition plan remains pending. No stable gain or novelty claim.

Both FastForward diagnostic positives also passed original-LoLA replay in results/target-stubborn-diagnostic-v1-lola-replay/report.json. This includes the later-phase Dekker witness and the focused guided-search witness.
