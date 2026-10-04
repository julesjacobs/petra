# Continuation status — completed DAG comparison, 2026-09-27

Goal active and incomplete: elegant, strong Rust Petri-net backend with publication-quality evidence. General superiority and novelty remain unproved. Latest request: harder test set. See research/harder-test-set-v3.md and benchmarks/development-catalog-v3.json. Single-core only. Never build/test/import on a host with live measurements. Reserved evaluation families remain uncollected and excluded from tuning.

## Host status

Linux comparison session 81442 completed with exit 0. All 170 rows and logs retrieved to results/linux-dag-sat-v2. Local diagnostic sessions 64847 and 10340 are terminal (exit 1 because independent checks failed). No measurements from this continuation remain live. Remote root: /home/jules/experiments/pvass-publication, host jules@jules-b650-aorus-elite-ax-v2 via tailscale ssh. Cargo +1.97.1; measurements CPU8, perf, enforced 2GiB.

## Completed comparison and harder-set evidence

Full 34-query Boolean-consistency v3 corpus, 5s, one repeat, original inputs:
- frozen predecessor: 8/34
- DAG v1 portfolio: 22/34 (15 positive, 7 negative)
- DAG v2 portfolio: 24/34 (15 positive, 9 negative)
- VerifyPN default: 5/34
- SMPT full portable with automatic reduction: 10/34

All 24 v2 native answers independently checked. No definitive disagreement, no tool errors. Candidate gains 16 over predecessor and loses none; gains 2 over DAG v1 and loses none. Ten queries unresolved by all five configurations. Complete artifacts results/linux-dag-sat-v2; audit research/linux-dag-sat-v2-analysis.{json,md}; script scripts/analyze_dag_comparison.py validates matrix completeness, native checking metadata and disagreement. Filters benchmarks/boolean-consistency-challenges-v2 are outcome-selected development data. Catalog v3 hashes verified. Original catalogs retained.

These synthetic source formulas are easy SAT instances; results concern reasoning through their net encoding, not general application superiority. The prior complete 368-query MCC comparison remains Rust298, Python frontend299, VerifyPN345: 70 Rust-unresolved, 58 VerifyPN-only, 12 jointly unresolved. Four-property focused application diagnostic showed no stable native coverage gain, versus VerifyPN4/4 twice. Hard application cases already exist; prioritize this gap.

Raw stress: 18 sources, 12 valid queries all solved twice by raw portfolio, 6 export timeouts. Diverse SER: 12 sources, zero exported (10 component-limit failures,2 memory limits). They are not solver-ready benchmarks. Fix scalable exact serial target construction before enlarging these parameter ladders; do not simply raise the semilinear component guard. Reserved evaluation v2: 8 families/16 models/256 slots, not collected or used for tuning.

## Implementation and freeze

Current Cargo/src/tests/vendor match results/solver-dag-sat-v2/source.tar.gz. DAG exact CNF encoding applies only to a certified acyclic one-token control projection; not arbitrary-net completeness. CLI dag-sat and portfolio-symbolic (40% DAG, then focused fallback); default unchanged. V2 derives final control markings from path choices, eliminating redundant control-counter arithmetic. Positive witnesses replay on original net. Negative RUP proofs independently checked after regenerating CNF. Both dag-cnf-rup-v1 and v2 supported in Rust/Python; legacy verification retained.

Files: src/dag.rs, src/dag_solve.rs, src/sat.rs, src/control.rs, scripts/dag_checker.py. Varisat0.2.2 vendored with interruption callback: vendor/varisat/PATCH.md and interrupt.patch. Always include vendor/varisat in source freezes. Cooperative interruption gaps documented; late results rejected. Design research/acyclic-control-sat.md. No novelty claim for conditional SAT encoding itself.

Validation: full Rust279pass/0fail/1preexisting ignored, DAG5groups incl independent BigInt BFS and cross-language CNF parity, integration3, SAT7groups incl160truth tables. Python DAG11 pass normal and optimized, original-input14 pass in vendor venv, clippy/release pass. Previous logs retained.
Mac v2 binary d165ac62dcfb3b9a7f8d33413c799f9f6595b422e13c3da5394f834c93642df7.
Linux v2 binary 37d1b8ae2e968ae7799372ab16bd3698c4291f472362b38c01a990b3eb114fc3.
Source13c662775324419a2df40d1afefe7064c3d3efb79efa8a545490585bb918782e.

## Preserved failures and unresolved checking limits

Corpus v1 SMPT fails missing XML description; v2 fails PNML identity names. V3 adds namespace and names; all canonical JSON/source CNF/Tina hashes identical. Failed runs retained; not solver defeats. Both compatibility smoke runs retrieved. Current valid full comparison supersedes compatibility uncertainty, without replacing previous artifacts.

results/dag-limits-diagnostic-v1: standalone dag-sat max_states2million (200million work),5s proposes three Rust-checked negatives, but proof outputs exceed default1MiB harness cap. Cases random3_n72_r480_s2026092702, random3_n96_r426_s2026092702, random3_n96_r480_s2026092701. Proof JSON1.2–3MiB. Diagnostic v2 raises cap16MiB; Python checker then exceeds its20million work bound (~6.4–6.7s). DO NOT credit these three answers. Pigeonhole p9/h8 stays unknown. Next experiment: explicit higher-work separately bounded independent check (e.g.200million work/30s/2GiB), or proof trimming. Preserve failed experiments. Resource TimeoutError currently classified error; distinguish exhaustion from malformed proof before changing.

Next priorities: stronger ordinary application performance, check large refutations, scalable raw targets, broader competitors, coherent novelty, independent evaluation. Read research/fastforward-baseline-plan.md before repeating investigation; FastForward uninstalled/unmeasured. Pro direction research/pro-publication-answer.md: coherent control-indexed token-flow refinement. Earlier status retained in research/continuation-status-before-dag-comparison.md.
