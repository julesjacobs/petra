# Component-choice discovery progress

Empirical diagnosis is saved in `results/raw-negative-choice-diagnostic-v2`.
The old greedy discovery's first pairlocked_n3 failure is transition 974,
crediting a second successful leave2. Its predecessor component trail is:
973 (no credited effect, component0), 974 (+leave2-success, component0->3),
963 (+reset, component3->3), 973 (no credited effect, component3). The reset
has been absorbed into the old component's free reset period. The next success
therefore requires translating the entire base 2*leave2-success without a
mandatory reset, and no destination permits it. This confirms the earlier
hypothesis about greedy component selection on an actual failed query.

The validated_v3 probe reaches 65,536 projected control nodes before exhausting
its unchanged work budget. A saved node includes two tokens in one observer
snapshot place and tokens in four other observer continuation places. Pending
observers can accumulate without bound. No failed component transfer appears.

The source now computes all valid component transfers, builds the reachable
(control, component) AND/OR graph, removes nodes having an enabled transition
with no surviving successor until a greatest fixed point, and extracts one
winning successor per transition. Existing certificate types and independent
checker obligations are unchanged. Before the full structural control
projection it tries the same algorithm on the empty projection, using one
eighth of discovery work; spent work is deducted before the full attempt.
This can prove response-language inclusion without enumerating pending readers.

Nine focused tests are being run, including the exact reset-choice regression,
a paired unsafe repetition, unrestricted-response unbounded pending requests,
and greatest-fixed-point cycle/AND obligations. Prior five raw-negative tests
already pass. No comparative timing claim is being made for the diagnostics.

The nine focused tests passed. With the new game search, both diagnostic
queries now produce negatives accepted by the independent Python schema plus
component checker on their original inputs:

- pairlocked_n3: 756 game nodes, 523 winning, 362 certificate nodes;
- validated_v3: 6 game/certificate nodes, zero control coordinates.

Artifacts: `results/raw-negative-choice-diagnostic-v3`. These are bounded
functional probes with diagnostics enabled, not a comparative benchmark.

Reviewer budget fixes are applied: a failed coarse attempt reserves its entire
allowance (including possible checker work), and control-vector clones are
charged before allocation. Full Cargo validation is running before freezing
and an input-inclusive comparison against the retained zero-negative pilot.

Full Rust suite completed: 304 passed, 0 failed, 1 pre-existing ignored. Clippy
passed after removing needless borrows; the failed first clippy log is retained.
Final release and source frozen in `results/solver-component-game-v1`:
- binary `fa24c7ee15a01cfe83d9ab16a16e2944eb418630307f2be46b9cac4b8078c174`;
- source `1117fe41777ad68bd943df0d240c05b54ce4c013689dafefa5b9033c0bf504f0`.

Local measurement session 37345 is LIVE: all twelve original diverse sources,
raw-negative, two repetitions, the existing 5-second input-inclusive harness,
2 GiB sampled process-tree memory. Output `results/raw-diverse-component-game-v1`.
No local builds/tests until this session is terminal. Baseline remains the
preserved `results/raw-diverse-schemas-v1` zero-negative pilot (one repetition).

Measurement session 37345 is now terminal (exit 0). Complete 24-row matrix:
12 queries x raw-negative x 2 repetitions. Four queries have independently
verified negatives in both repetitions: write_skew_n3_pairlocked and
optimistic_v{3,5,9}_validated. All eight other queries remain solver-unknown;
the larger pairlocked cases report the original discovery work limit. No
checker failure or contradictory definitive answer occurred. The retained
prior schema pilot solved 0/12; the new pilot solves 4/12. This is a development
coverage result, not a general superiority claim or a matched runtime study.

All local Cargo/diagnostic/measurement handles owned by this agent are terminal.
Source changes are confined to src/raw_negative.rs and its inline tests; proof
format and checkers are unchanged. Full results/report:
`results/raw-diverse-component-game-v1/REPORT.md`.
