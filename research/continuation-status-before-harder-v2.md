# Continuation status — 2026-09-27

The goal remains active and incomplete. General superiority, publication novelty and independent evaluation are unproved. This turn made verified progress through automatic raw negative proofs, a complete measured raw portfolio, and an ordinary-solver memory diagnostic.

## Live work

All local and Linux benchmark/build/test sessions from this turn are terminal. No agent has ongoing assigned work. Last full Rust test session73212 ended exit0. It is safe to build/develop after checking for any newly started workloads. Keep single-core comparisons; never build/test/import on a host with live measurements.

## Current source and verified raw result

Cargo/src/tests exactly match `results/solver-raw-portfolio-v1/source.tar.gz`.
- Binary SHA256: ce95ebb36dff0e94ddf0583cf2091362c6e69181f2a667c1e2bd05640f3e18e8
- Source SHA256: 804e628a774c5f89b5d431ef0fe4595fd90306696a32f3253eea41abe75b7dee
- Final full Rust suite: 242 passed, zero failed, one pre-existing ignored. `research/raw-portfolio-final-tests.log`.
- All-target clippy passed. Python raw suites: 38 passed.

`raw-negative` automatically discovers credited component invariants in src/raw_negative.rs. It structurally infers completion-place response credits, selects controller places outside responses/credits/source-transition outputs, and closes pairs of projected controller marking and original serial component. Every edge has exact nonnegative affine coefficient witnesses. A sparse exact natural-monoid search with limits finds coefficients. The auxiliary LP conservation search was removed; finite controller closure itself is checked. Rust checker src/raw_invariant.rs and independent Python scripts/raw_invariant_check.py both check original arcs, initial membership, complete enabled closure, and all affine maps. Both use indexed transition candidates plus full weighted enabling checks; unsupported/exhausted proofs never establish unreachability.

`raw-portfolio` allocates up to one quarter of remaining solver time to raw-negative, then gives the remaining time to raw-potential if inconclusive. It preserves one shared deadline and returns a certificate or replayed witness. CLI --verify checks either raw verdict. The raw benchmark harness accepts negatives only after Python checking; its explicit negative verification work limit is100×max_states (20million by default), with the same wall/RSS deadline. The checker library default is still1million for standalone calls.

`results/raw-stress-portfolio-v1` completes all36rows: all12valid queries solved in both repetitions (9positive,3negative), all18sources retained including6export timeouts. 10s input-inclusive deadline including independent checking,2GiB sampled process-tree RSS, shared Mac. New negatives: counter_d31_s16_locked (~0.69–0.74s), replicas_n8_locked (~0.22–0.23s), replicas_n10_locked (~0.93s). This is one deployed portfolio, not the union of separate modes. Report: research/raw-portfolio-v1-results.md; machine-readable analysis beside it; proof argument: research/credited-component-invariants.md.

Preserve intermediate failures: raw-stress-negative-v1 (0verifiednegatives), raw-stress-negative-indexed-v1 (1), raw-stress-negative-structural-v1 (3negative and9positive in separate modes). Initial checker work cap failures have separate diagnostic rechecks; these never overwrite the failed benchmark results. Frozen solver directories and every runner snapshot remain.

## Ordinary-net competition and memory problem

Full paired stress run `results/linux-stress-paired-frontends-v1`: 368properties,5s,CPU8,perf,2GiB,1repeat; Python frontend299, Rust frontend298, VerifyPN345. Both native labels use the same older engine binary. Analysis: research/linux-stress-paired-frontends-v1-analysis.md.

Fixed an exact wasted-allocation bug: state_equation/integer_equation checked max_rows only after building enormous dense originals. A shared checked original_row_count now rejects before allocation; focused regression verifies zero constructor calls above budget.

Remote new ordinary engine build: `/home/jules/experiments/pvass-publication/results/linux-solver-raw-negative-structural-v1` (contains frozen source, build log, binary, hashes). It predates the raw-portfolio CLI addition, but ordinary engine code matches current. Linux build uses `/home/jules/.cargo/bin/cargo +1.97.1`.

Completed `results/linux-row-preflight-diagnostic-v1`:4outcome-selected properties×3methods×2repeats, same single-core5s/2GiB/perf protocol. Predecessor6OOMruns; newbuild0OOM but6timeouts. Both native builds solve1/4, VerifyPN4/4. No coverage gain. Newbuild includes earlier compact search changes, so not a pure row-guard ablation. Report/runs/environment retrieved locally, additional artifacts remain remote. See research/linux-row-preflight-diagnostic-v1-analysis.md. Dense `count_plan::characteristic` still allocates P×T before limits; sparse routing/representation remains next concrete work.

## Benchmark state and next work

`benchmarks/stress-challenges-v1` contains exact filters over unchanged368-property stress corpus:70native unresolved,62both-candidate unresolved,12all-three unresolved,58VerifyPN-only,11native-only. Outcome-selected development views only; retain full denominator.

`benchmarks/reserved-evaluation-v2.json` reserves16models/256slots from8recorded-unused families. It is selection-only, uncollected and unmeasured. Keep every instance of these families out of tuning; historical exposure/model-relatedness audit still needed before independence claim. Six raw export failures remain an exporter limitation.

Next priorities: improve ordinary-net sparse fallback and search/reduction so the memory fix yields answers; run fair single-core full-corpus comparisons including SMPT and FastForward; expand genuinely diverse raw program families while preserving reserved evaluation; audit novelty against prior invariant/control-abstraction methods. The raw development corpus is now solved among valid exports, but the ordinary-net gap is substantial. Optional publication-emphasis clarification is pending; do not ask again or block work on it.

Historical context is preserved in research/continuation-status-before-raw-negative.md and the individual experiment reports.
