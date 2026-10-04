# Continuation status — automaton targets and relevance, 2026-09-27

Goal active and incomplete. This turn made substantive progress: twelve previously failed source exports now yield valid exact queries; new automaton guidance gains one verified raw answer; application relevance reduction improves matched JoinFree coverage35→46/48. No general superiority or publication novelty claim.

## LIVE PROCESS — inspect first

Session57518 runs Linux full368-property MCC stress comparison: results/linux-stress-relevance-v1, expected1104rows (368×3×1repeat). Methods before=portfolio-focused/linux-solver-dag-sat-v2, after=portfolio-focused/linux-solver-relevance-automaton-v1, VerifyPN default.5s,CPU8,perf,enforced2GiB,original inputs,separate checking,seed20261004. Plan research/linux-stress-relevance-v1-plan.json; progress research/linux-stress-relevance-v1.log. DO NOT build/test/import/mutate inputs/scripts on Linux while this runs. Poll57518 and verify terminal before retrieval or other heavy remote work. Do not restart from observation timeout.

Linux: tailscale ssh jules@jules-b650-aorus-elite-ax-v2; /home/jules/experiments/pvass-publication; /home/jules/.cargo/bin/cargo +1.97.1. Remote rg is absent; use grep or Python. Mac and Linux are independent hosts. All other sessions from this turn terminal (95376,11363,96946,85431,17742,94051,80766,94117,5639,13559,72897,35682,80562). No local measurement live.

## Source state and freezes

Current Cargo/src/tests/vendor match results/solver-automaton-potentials-v1/source.tar.gz (fb0af885f90902fdcac6a93b537379bc09c4b9dd93fca74c3a8dcb019ce5be4d). Mac binary6c866dbfce8414532c2985eacaba35de5cee9ef5840244a7308c3293d1eb321c.
Earlier combined relevance+NFA membership freeze: results/solver-relevance-automaton-v1 and results/linux-solver-relevance-automaton-v1. Linux live run uses this earlier source/binary. Later changes only concern raw automaton target guidance and missing-v1-field validation; ordinary PNML solver code unchanged. Keep hashes/configurations separate.
Frontend old/new freezes results/frontend-before-automaton-v1 and results/frontend-automaton-v1; new ser binary09091ecce01b0bc39c8b90f444983fb690b3571c12f547a843d4e12bfe05e882.
Always include vendor/varisat in solver source freezes.

## New raw target representation

Optional ser --export-raw-automaton emits ser-raw-v2: unreduced original request-tracking net plus exact serial response NFA, bypassing Kleene/semilinear expansion. NFA fields states,initial,accepting,edges; each edge source,target,response(original place ID), one emitted token. Frontend all states accepting. V1 export preserved. Patch/setup scripts/ser-raw-automaton-export.patch and scripts/setup-raw-automaton.sh; vendor/.../RAW_EXPORT.md documents format.
Rust raw_target.rs accepts either v1 semilinear or v2 automaton, with strict format/target checks. Exact v2 membership uses memoized(state,residual response vector) exploration; limits propagate unknown. Missing v1 semilinear field is rejected by custom deserialization. Raw search replays full original traces. raw_negative/raw_invariant explicitly reject automaton targets; no v2 negative certificate yet.
raw_potential.rs now derives the same coordinate/difference sufficient goals directly from maximum-weight NFA paths. Reachable positive cycles conservatively skip a form; otherwise maximum accepting weight bounds every serial vector. Full target checked on every result.
Python raw_automaton_check.py independently decides fixed-vector membership by nonnegative integer edge counts, Euler balances and strictly descending rooted-support ranks. Z3 UNSAT verifies nonmembership; unknown/deadline is never accepted. raw_stress_worker validates both schemas and uses this checker. benchmark_stress_raw snapshots it and recognizes its label. raw-z3 explicitly unsupported on v2. collect_stress_raw --automaton selects new exporter.
Design/proof: research/raw-automaton-target.md. No novelty claim for these standard constructions.

Validation: frontend4tests incl bounded v1/v2 semantic agreement; unchanged v1 bytes and deterministic v2 smoke. Combined full Rust284passed,0failed,1preexisting ignored before final raw schema/potential additions. Final4raw-automaton integration tests (1024 membership cases plus generated-goal checks), existing raw_potential tests, clippy and release pass. Python42raw regression tests pass. Logs research/{automaton-*,raw-automaton-*}. No full Rust rerun after final two raw-only tests; focused validation covers those changes.

## New harder raw benchmark and results

benchmarks/raw-diverse-automaton-v1: all12 previously frozen diverse sources exported,8.90s total exploratory Mac collection; largest query42MB. V1 had10component-limit failures+2memory failures; retain benchmarks/raw-diverse-v1 as failed representation track, not12extra sources. All12schemas validated through bounded pilot.
Initial results/raw-diverse-automaton-v1 rejected valid checker labels in parent (worker-protocol-error); retained. Fixed label dispatch, regression-tested, reran full pilot results/raw-diverse-automaton-v2: raw-bfs4/12,raw-search5/12, all accepted positives independently checked,7joint unknown.
Final results/raw-diverse-automaton-potentials-v1:48rows=12×2methods×2repeats,5sinput-inclusive,sampled2GiB,Mac. raw-search5stable positives; raw-potential6stable positives. Gains optimistic_v9_aba, no losses. All six intended nonserial programs verified; six source-expected serial programs remain UNKNOWN, not proved negative. Full analysis research/raw-diverse-automaton-potentials-v1-analysis.json. Catalog benchmarks/development-catalog-v4.json keeps alternate representations and existing tracks separate.

## Application relevance reduction

src/relaxed.rs retains all transitions changing target-support places, then recursively positive-incidence producers of retained input guards. Compacts actions/facts once, preserving original IDs. Projects markings onto retained guards and target support; full original replay remains. Removing omitted transitions only increases retained guard availability and leaves target coordinates unchanged, preserving existential target reachability over naturals. Positive-only implementation still returns unknown on exhaustion/overflow. Design research/relaxed-relevance-slice.md;12relaxed integration tests incl original replay of discarded outputs, weighted reads, cleanup, differential BFS.
JoinFree1000 RC01 shrinks8001→16transitions and5001→10guard places. DLC/AutoFlight do not shrink.

Completed results/linux-relevance-diagnostic-v1:4previous selected cases×3methods×2repeats. Before/after solve same2/4twice;VerifyPN4/4twice. JoinFree median1.349→0.762s,18.10→14.16billion instructions;VerifyPN0.157s/1.01billion. Current portfolio spends~0.6s in earlier phases before now-small search. Analysis research/linux-relevance-diagnostic-v1-analysis.{json,md}.
Completed results/linux-joinfree-relevance-v1:all48properties×4methods×1repeat,192rows. Before35,after46,standalone relaxed-focused46,VerifyPN46.11native gains,no losses; two native-only and two VerifyPN-only. All native answers independently checked; no definitive disagreement. On44common solves native-portfolio/VerifyPN median wall1.38/geomean1.11,median instructions1.71; standalone sliced search median wall0.73/geomean0.59,median instructions0.47. Conditional timing excludes timeouts; keep full48denominator. Analysis research/linux-joinfree-relevance-v1-analysis.{json,md}. Source expected signs not used. One-repeat selected development family, not generalization.

## DAG checking followup

--validation-dag-work now configurable, default20million unchanged; request/report dag_check_max_work propagated. Internal TimeoutError classified unknown/checker-resource-limit, malformed proof remains error. Agent53focused validation tests pass, last20after direct path adjustment. Changed scripts benchmark.py,bounded_validation.py,rust_original_validation.py,benchmark_smpt_classic.py and tests.
results/dag-proof-recheck-v3 rechecks3preserved large negative outputs at200million work/30s/16MiB output/2GiB sampled RSS. n72_r480_s2026092702 verified in10.94s; n96_r426_s2026092702 verified in27.22s; n96_r480_s2026092701 timed out and remainsunknown. No solver rerun; do not add these to24/34full comparison. Earlier failures retained. Script research/recheck-dag-proofs-v3.py, report research/dag-proof-recheck-v3.md.

## Previous evidence and next actions

Full DAGv2 synthetic Linux170rows remains new24/34,before8,DAGv1=22,SMPT10,VerifyPN5;10joint unknown; all native independent checks. Preserve synthetic scope, corpusv3 compatibility metadata, failure history. Ordinary old full368 remains native298/368 vsVerifyPN345 until LIVE run completes.

Next:
1. Finish/poll57518, retrieve full1104rows and audit complete matrix. Positive aggregate may follow unknown earlier branches: require at least one independently checked reachable branch, not that every check label is python-. Negatives need allbranches checked. Report regressions and full family denominators.
2. Six newly exported serial targets still lack negative proofs. Agent proposed certifying linear path schemas u0 v1* u1 ... vk* uk as NFA sublanguages (each vi loop at current anchor), then using their base/periods with existing component invariants; proposal only.
3. A coherent shared relevance reduction could remove portfolio overhead across engines, but negative proof lifting requires explicit independent checking and must not silently reuse reduced-net certificates as original-net proofs. Current reduction is only within positive search.
4. Broader comparison/novelty/heldout still outstanding. Eight reserved families16models256slots remain untouched. FastForward uninstalled/unmeasured; research/fastforward-baseline-plan.md describes concrete compatibility issues. Optional user question about adding FastForward suite was asked this turn; no answer yet, not a blocker for current work. Do not ask again.
5. Goal remains active; do not claim publication readiness or a record.

Previous status retained research/continuation-status-before-automaton-relevance.md.
