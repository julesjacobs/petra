# Continuation status — harder development corpus, 2026-09-27

The goal remains active and incomplete. General superiority and publication novelty are unproved. The latest request is for a harder test set. This turn adds a measured synthetic development ladder and exposes a serious raw SER export limitation. Keep reserved evaluation families out of tuning. Single-core comparisons only; never build/test/import on a host with live measurements.

## Benchmark additions

- `benchmarks/boolean-consistency-v1`: 34 frozen original PNML/XML properties, canonical JSON, Tina inputs and source DIMACS. Random 3-SAT at four sizes, three ratios, two seeds; five paired positive/negative pigeonhole sizes. Selection fixed before solver outcomes. Generator `scripts/generate_boolean_nets.py`; four tests pass, including independent exhaustive state-space versus truth-table agreement on 40 tiny random cases and pigeonhole cases. Proof of encoding in `research/boolean-consistency-v1.md`.
- Linux pilot `results/linux-boolean-consistency-v1`: all 34, existing frozen `linux-solver-raw-negative-structural-v1 / portfolio-local` versus unrestricted VerifyPN, original inputs, 5 seconds, one repetition, CPU8, perf, enforced 2GiB, separately bounded native checker. Source changes below are NOT included. Plan `research/boolean-consistency-v1-plan.json`. Completed all68rows, retrieved full results: Rust8/34, VerifyPN5/34,25jointly unresolved,0definitive disagreements,0OOM,54outer timeouts,68perf runs. All8Rust witnesses independently checked. See research/harder-test-set-v2.md and research/boolean-consistency-v1-analysis.json. Outcome-selected filters in benchmarks/boolean-consistency-challenges-v1. Both hosts are idle; all collection/build/measurement sessions are terminal.
- Separate source-formula oracle: 10 SAT, 14 UNSAT among random formulas; SAT assignments checked directly, UNSAT has no independently checked proof. Every Z3 source check took <5ms on Mac. These nets diagnose representation/symbolic reasoning, not intrinsically hard SAT instances or representative application superiority.
- `benchmarks/diverse-ser-programs-v1`: 12 sources from new ring-write-skew and optimistic-ABA families. All source expectations are arguments, unverified at the exported-net level. Five generator/finite-model tests pass. Source integrity is frozen; its documentation is hashed by manifest, so put new results in separate documents.
- `benchmarks/raw-diverse-v1`: all12 exports attempted at60s/2GiB sampled RSS/1GiB sampled artifacts. 10 semilinear component-limit panics,2 memory limits,0 valid queries. All parsed. `results/raw-diverse-v1` contains twelve export-unavailable rows; zero solver attempts. See `research/diverse-ser-v1-collection-results.md`. Raw export still eagerly computes the serial automaton's semilinear Parikh image before emitting files. Raising the >30-component guard just exposes exponential enumeration; a scalable exact target representation/construction is needed.
- `benchmarks/development-catalog-v2.json` indexes these separate tracks, existing full368 MCC stress corpus and18 raw stress sources (12valid,6export timeouts). Do not pool these into one performance score.

## Solver work carried over and completed

`count_plan.rs`: overflow-safe dense-allocation preflight including incidence+slack expanded system; route oversized initial/refinement systems to existing sparse solve with deadline and consumed work preserved.
`search.rs`: shared Arc<StoredMarking> nodes/seen and one scratch marking; indexed ordered successor checks.
`quotient.rs`: compact representatives and scratch; indexed successors, inner deadlines, explicit unknown on target arithmetic error;512bounded differential cases added.
`backward.rs`: exact sparse BigInt hurdle/effect composition and sparse region targets; compact forward states and indexed successors; bound beam storage; release summaries before forward phase. Positive-only original replay authority unchanged. Six focused tests including sparse/dense composition, read arcs, huge effects, resource/overflow checks.
`relaxed.rs`: new `solve_focused`: helpful-only search for first third of allotted time, then original broad search on unknown within shared deadline. New CLI `relaxed-focused`, `portfolio-focused` using same causal/local-closure schedule with focused relaxed phase. Only positive witnesses can be returned.
`main.rs`: optional VASS_PORTFOLIO_PROFILE=1 phase start/end stderr logs; disabled in benchmarks.

Validation: full suite262passed,0failed,1preexisting ignored before the final two focused tests; all9relaxed tests after those additions pass, both variants cover80bounded differential cases. Focused20-step/128distraction fixture uses21states; nonhelpful fallback fixture finds the only witness. All-target clippy and release build pass. Logs `research/ordinary-sparse-combined-*.log`.

Frozen Mac candidate: `results/solver-ordinary-focused-v1`.
Binary d333863bca37a99bcedd0066e91c09c25399316cda25d6ee5fcd1f563c4d811a.
Source 6c72a0638c2d3d273d71206e7f57fd5f66d8faa63e96def31d7d3c969996a049.
Current Cargo/src/tests match this freeze. No performance result yet for these last changes.

Intermediate preserved: `results/solver-ordinary-sparse-v1`, `results/ordinary-phase-profile-v1`. Instrumented initial diagnostic: DLC7b RC00 solved by relaxed, AutoFlight48b RC01 OOM in quotient dense representatives, JoinFree1000 RC01 OOM in backward dense summaries. Last two fixes above are unmeasured. Repeat bounded diagnostics before full Linux comparison; instrumented timings are not competition results.

## Existing verified results and remaining work

Previous raw portfolio solves12/12valid stress queries twice (9positive,3negative); frozen `results/solver-raw-portfolio-v1`. Preserve all18sources including6export failures. Report `research/raw-portfolio-v1-results.md`.
Existing full ordinary Linux stress comparison: candidate Python299/368, candidate Rust298/368, VerifyPN345/368. Hard views70native-unresolved,62both-native-unresolved,12all-three-unresolved,58VerifyPN-only,11native-only; outcome-selected development only. Reserved evaluation v2:16models/256slots from8recorded-unused families; selection only, exposure/relatedness audit outstanding.
Next: fair measurements of new solver, original-net symbolic reasoning for Boolean consistency, scalable raw serial target construction, broader ordinary competition including SMPT/FastForward. Read `research/fastforward-baseline-plan.md` before repeating research. FastForward remains uninstalled/unmeasured. Avoid claiming a record from outcome-selected or synthetic views.

Old status retained in `research/continuation-status-before-harder-v2.md`.
