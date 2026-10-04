# VerifyPN witness audit

All **22 positive frontier results** in `research/verifypn-frontier.json` have independently replayed witnesses on the original canonical JSON nets. The remaining result, `JoinFreeModules-PT-0005__RC09`, is an **unchecked external negative**. These are development properties selected because VerifyPN solved them and the earlier Rust portfolio did not; they are diagnostic evidence, not an unbiased performance comparison.

The checker `scripts/audit_verifypn_traces.py` extracts complete XML traces, resolves transition IDs in the original net, checks enabling before every firing, updates the original marking with integer arithmetic, and checks all target branches. It also evaluates the original XML endpoint predicate independently, including AG counterexample polarity. Branch and original-property XML hashes are checked against the manifest. Every transition name resolves; no unexpanded names were encountered. Unindexed transitions in VerifyPN traces are retained and replayed. The checker does not use the trace's token annotations or reduced transition indices.

Reproduce:

```sh
python3 scripts/audit_verifypn_traces.py \
  --manifest benchmarks/mcc-publication-development/manifest.json \
  --selection research/verifypn-frontier.json \
  --logs results/publication-original-causal-verifypn \
  --output research/verifypn-witness-audit.json
```

The audit makes no shortest-witness claim. FIFO depth below is the longest token-provenance chain under one valid FIFO assignment of consumed tokens. Plateau means consecutive firings that leave every place mentioned by any original target branch unchanged; this implies every direct target-value heuristic is constant throughout that interval. Expanded counts are VerifyPN's reported reduced-net search counts, not independently measured counts.

| Query | Original steps | FIFO depth | Longest target-place plateau | Unindexed steps | Reported expanded |
|---|---:|---:|---:|---:|---:|
| Echo-PT-d02r15__RC00 | 102 | 16 | 101 | 1 | 102 |
| Echo-PT-d02r15__RC01 | 108 | 18 | 107 | 1 | 106 |
| Echo-PT-d02r15__RC02 | 58 | 16 | 45 | 1 | 56 |
| Echo-PT-d02r15__RC03 | 114 | 16 | 113 | 1 | 112 |
| Echo-PT-d02r15__RC13 | 7 | 7 | 6 | 1 | 5 |
| Echo-PT-d02r15__RC14 | 85 | 16 | 77 | 1 | 83 |
| CANConstruction-PT-020__RC03 | 20 | 16 | 19 | 12 | 13 |
| CANConstruction-PT-020__RC05 | 9 | 9 | 8 | 6 | 2 |
| CANConstruction-PT-020__RC06 | 38 | 25 | 37 | 22 | 29 |
| CANConstruction-PT-020__RC07 | 7 | 7 | 6 | 4 | 2 |
| CANConstruction-PT-020__RC09 | 20 | 13 | 19 | 12 | 7 |
| CANConstruction-PT-020__RC12 | 29 | 17 | 28 | 17 | 21 |
| CANConstruction-PT-020__RC14 | 37 | 22 | 36 | 22 | 14 |
| CANConstruction-PT-020__RC15 | 12 | 12 | 10 | 7 | 4 |
| CANConstruction-PT-040__RC00 | 38 | 22 | 37 | 22 | 18 |
| CANConstruction-PT-040__RC04 | 38 | 19 | 37 | 22 | 39 |
| CANConstruction-PT-040__RC05 | 19 | 14 | 18 | 12 | 6 |
| CANConstruction-PT-040__RC08 | 28 | 19 | 27 | 17 | 10 |
| CANConstruction-PT-040__RC10 | 101 | 40 | 100 | 57 | 184 |
| CANConstruction-PT-040__RC11 | 29 | 17 | 28 | 17 | 16 |
| CANConstruction-PT-040__RC14 | 21 | 15 | 20 | 13 | 7 |
| CANConstruction-PT-040__RC15 | 20 | 16 | 19 | 12 | 13 |

## Concrete algorithm opportunities

1. **Depth-first tie-breaking on heuristic plateaus.** In `src/search.rs`, `Reverse((score, child))` chooses the oldest state among equal scores. `src/guided.rs` likewise prefers smaller depth in one queue. VerifyPN's `HeuristicQueue::weighted_t` in `vendor/verifypn/include/PetriEngine/Structures/Queue.h` chooses the newest state among equal distances, explicitly giving DFS behavior. Echo RC00 and RC03 have 101- and 113-step plateaus, while FIFO causal depth is only 16. VerifyPN reports expanding 102 and 114 states, respectively. This is strong diagnostic motivation for an equal-score LIFO/deeper-state ablation, possibly with bounded exploration/restarts to avoid pathological plateaus. It is not yet evidence that changing one comparator closes the gap, because transition order, reductions and stubborn sets also differ.
2. **Necessary-enabling dependency guidance.** All 22 witnesses use every transition at most once. These examples therefore do not require large transition counts or acceleration merely to obtain a positive witness. A target achiever may require a long chain of currently missing prerequisites. Propagating target demand through producer transitions can guide plateau traversal; many Echo steps are concurrent token dependencies rather than a single 114-deep chain. Keep such guidance as ranking until a sound pruning proof exists, and replay every result.
3. **Trace-preserving serial fusion.** CAN logs show only rule B applications, with 1,277–1,358 applications in size020 and 5,002–5,120 in size040. Rule B implementation is at `vendor/verifypn/src/PetriEngine/Reducer.cpp:421`: it considers a non-query place with one consumer and one or more producers and applies further side conditions. Its source comment's one-producer description is narrower than its actual guard. The exact guard must be rederived before implementing an equivalent reduction. CAN040 RC10's 101-step witness contains 57 unindexed expansion steps; reductions substantially shorten the sequence explored. This supports an explicit macro-transition with exact original-sequence replay as a useful design, rather than assuming all of the advantage is faster per-state search.
4. **Sparse marking and successor representation.** Echo has 2,127 places and 1,674 transitions; CAN040 has 3,682 places and 6,720 transitions. The current simple search loops over all transitions and stores/clones dense markings. VerifyPN reports state compression and stubborn sets. After plateau handling, incremental enabling updates and compact marking storage are concrete runtime opportunities; no speedup has been measured here.

Echo reductions are modest in transition count: six removed transitions, with rule A and I applied once each; 234–235 places removed. CAN reductions remove 190–198 transitions in size020 and 396–400 in size040. These are log observations. The logs advertise query reduction, structural reduction, SAT/SMT, explicit search, state compression and stubborn sets; this does not establish how much each contributes.

## Baseline fairness correction

The archived competitor command contains **`--trace -x 1`**. VerifyPN prints “Rule H, J, R, S, Q disabled when a trace is requested.” The source independently confirms early `reconstructTrace` returns in those five reduction routines. Trace mode also stores predecessor information. Therefore label this baseline **VerifyPN with trace reconstruction**, not unrestricted default VerifyPN. Its positive outcomes now have original-net checks; that trust benefit does not make it a best-configuration performance baseline.

Measure unrestricted VerifyPN separately without `--trace`, under the same original-input deadline/memory/affinity configuration. Preserve trace runs as a verification/ablation track and optionally obtain diagnostic traces outside the timed unrestricted run. Do not attach an unrestricted timing to a trace-mode invocation, and do not assume the rule restriction hurts every instance monotonically: reduction time and search time interact. Negative results remain external tool verdicts unless independently certified.

This audit ran only a small read-only Python replay (about 0.12 seconds reported by the command wrapper) and source/log inspection while measurements were live. No solvers, builds or timing experiments were launched.
