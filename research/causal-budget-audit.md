# Causal portfolio budget audit

Read-only source/result audit, 2026-09-27. No solver, build, or test was run. The continuation benchmark was still running; the numbers below describe a fixed partial snapshot, not the completed development comparison.

## Evidence snapshot

Inputs:

- `results/publication-causal-portable-clean2/runs.jsonl`: 401 records, SHA256 `bc6d74c4253906810a305cf11bc5b07207503c6b059573f04ae60cc972bb8680`.
- `results/publication-causal-portable-clean2-rest/runs.jsonl`: first snapshot of 230 records, SHA256 `bc95e783374cc58b3d5a04d2a1082d8bb1cf246ad57f10103149c96799fc9cbf` (this live file subsequently grows).
- Continuation `SEGMENT.json` selects all 133 complete original properties from the first segment independently of outcomes. Discard its incomplete original property, then retain only complete three-method properties from the continuation snapshot.

This yields 209 complete properties. Counts are:

| Method | Reachable | Unreachable | Unknown | Solved |
|---|---:|---:|---:|---:|
| frozen-v2 | 53 | 80 | 76 | 133 |
| portfolio-causal | 57 | 124 | 28 | 181 |
| SMPT portable, plain WALK | 62 | 81 | 66 | 143 |

| Family | Properties | v2 solved | causal solved | SMPT solved |
|---|---:|---:|---:|---:|
| AutoFlight | 32 | 32 | 32 | 32 |
| CANConstruction | 32 | 0 | 13 | 23 |
| CircularTrains | 32 | 29 | 32 | 1 |
| CloudOpsManagement | 17 | 17 | 17 | 17 |
| DLCflexbar | 32 | 19 | 32 | 23 |
| Echo | 32 | 5 | 24 | 30 |
| JoinFreeModules | 32 | 31 | 31 | 17 |

There are **zero frozen-v2 solved to portfolio-causal unknown regressions** in this snapshot. Every negative success from `results/publication-sparse-linear/runs.jsonl` whose property occurs in these 209 is also solved by portfolio-causal. Thus the conjecture that causal's shortened root-dual slice loses standalone sparse-negative successes is currently unsupported by these data. The old run's timings were contaminated, and its success set supplies capability evidence only.

Three prior sparse-primal witnesses *are* missing from causal:

| Property | Independently replayed old witness branch | Causal result |
|---|---:|---|
| CANConstruction-PT-020__RC05 | 0 | unknown; outer timeout on branch 0 |
| CANConstruction-PT-020__RC12 | 0 | unknown; outer timeout on branches 0 and 1, branch 2 refuted |
| CANConstruction-PT-020__RC15 | 1 | unknown; branch 1 outer timeout, other branches refuted |

Source: `results/sparse-primal-frontier-pilot/runs.jsonl`; successes are `python-witness` checked. Old observed property walls are 0.348, 0.078, 0.112 seconds respectively, but orphan contamination precludes timing comparisons or inferring that a 100ms slice would reproduce them. These establish valid witness availability, not a measured scheduling explanation. The causal outer-timeout records contain no phase diagnostic, so one cannot identify the failing internal phase from them.

Native runs consume pretranslated JSON; SMPT consumes original PNML/XML with conversion/reduction inside its deadline. The partial solved counts are not a matched end-to-end performance comparison. External SMPT answers lack independent proof checking. See `research/publication-protocol.md` for the required fairness tracks.

## Actual budget allocation

`src/main.rs::causal_portfolio` grants causal `min(0.20 * branch_budget, 500ms)`, then calls `improved_portfolio` with remaining time. `src/causal.rs::Search::visit` gives the root dual at most one quarter of the causal remainder (125ms before setup overhead for a 5s one-branch query). It then grants the integer model half of the remainder (about 187.5ms if the dual consumes its allowance); realization/support recursion shares the rest. Setup and proof checking also consume time. Descendant nodes repeat this division. Unknown causal details are discarded when falling back, so the eventual answer cannot diagnose the earlier attempt.

By comparison, `src/main.rs::sparse_portfolio` (`portfolio-v3`) gives sparse dual the full `min(0.20 * branch_budget, 500ms)`, then v2. It contains no sparse integer candidate phase. `src/count_plan.rs::solve_sparse` grants integer discovery half its own remaining deadline without first running dual. Its support refinement differs from causal's checked universal split, so a witness discrepancy can also reflect candidate/refinement behavior.

`scripts/benchmark_smpt_classic.py::native` allocates `(5s - observed_prior_branch_wall) / remaining_branches`. Hence a four-branch property's first causal slice is at most 250ms, its root dual at most 62.5ms, and its first integer attempt roughly 93.75ms if dual exhausts its slice. The scheduling pressure is concrete; causation of the observed losses is not yet measured. `improved_portfolio`/`next_portfolio` do not retry `solve_sparse`; their older count-plan engine is different.

## Recommended next experiment and minimal change

First run a clean diagnostic ablation after the current benchmark terminates: existing `portfolio-v3`, standalone `causal-state-equation`, and standalone `sparse-count-plan` on the three witness-loss properties, plus all CANConstruction and Echo development properties with the same original-property budget. Freeze inputs and binary and retain every property; diagnose on the three named losses without using evaluation data. Also repeat portfolio-causal on this set to distinguish scheduling stability from a deterministic algorithmic difference. Compare actual portfolios, not result unions.

Add lightweight phase diagnostics (elapsed time, dual outcome, model count, refinement count) to stderr or an optional outcome field, preserving causal diagnostics when the fallback returns. This is the smallest evidence-producing implementation change. Existing method return values do not distinguish numerical failure, LP timeout, or exhausted search well enough to explain the missing witnesses.

The next proposed scheduling variant should preserve the successful sparse-dual allocation and explicitly give sparse integer discovery a useful slice: root dual up to `min(0.1*T, 500ms)`, then sparse candidate/realization up to `min(0.2*T, 1s)`, then v2 with the actual remainder. Use an experimental method name; leave the default and frozen baselines unchanged. This is a proposal to test, not an established improvement. It preserves a 500ms root-dual opportunity at T=5s while increasing first integer discovery from at most ~187.5ms to ~500ms. A smaller 500ms primal stage is also worth testing if 1s harms fallback coverage. Separate root dual from recursive dual scheduling if integrating into causal so the same root LP is not solved twice.

Do **not** simply increase the root dual from 125ms to 500ms inside causal's unchanged 500ms total slice: that can eliminate candidate discovery, directly opposing the witness-loss evidence. Nor does switching to v3 alone target these three losses: v3 has no sparse candidate stage. v3 is still an essential cheap baseline to assess whether causal refinements add anything over sparse dual plus v2 on this corpus.

## Coherent next token-flow strengthening

`src/token_cut.rs::bounds` gives every noncontrol edge upper bound infinity. As independently derived in `research/token-cut-review.md`, data cut sets must then be successor-closed. In a strongly connected controller, all data flow feasibility follows from total balance and provides no stronger data condition than the state equation (terminal control constraints can still help).

Add certified nonnegative place subinvariants as the next coherent extension. An exact integer vector w with w>=0 and w*delta(t)<=0 for every original transition proves w*m<=B=w*initial at every reachable marking. For each w_i>0, it yields the global finite bound floor(B/w_i). At control mode q, subtract the exactly known selected-control contribution before dividing, yielding a sound mode-dependent bound for a noncontrol place. Discover weights numerically if useful, but check nonnegativity, original-incidence inequalities, and B with BigInt; store weights in certificates and reconstruct bounds independently in Python.

A finite source bound U enables y_e,i<=U*n_e and residual capacity (U-l)*n_e. Consequently zero candidate count yields zero capacity legitimately, unlike replacing a truly infinite bound by zero. Nontrivial cuts inside strongly connected controllers become available. Bounds below a transition's preweight require excluding that edge only after certified impossibility, or forcing its count to zero in the master; never pass a negative residual capacity. Global final-marking bounds can additionally strengthen the master. This remains one flow-relaxation method rather than adding unrelated search heuristics.

Suggested mathematical regression: a two-mode strongly connected controller with a bounded data place where state equation is feasible but a finite-capacity subset cut is violated; enumerate short concrete paths and check every emitted cut, verify full bounded-moment LP versus lazy separation, and reject altered invariant weights in both checkers. Finite bounds are a sound expressiveness extension, not proof of complete reachability or literature novelty.

## Completed diagnostic and causal search revision

The full original-input macOS comparison (`results/publication-original-causal-verifypn`) completed: frozen v2 181/256, causal 228/256, VerifyPN 251/256; no errors or definitive disagreements. VerifyPN's 23 additional properties are 16 CAN positives, six Echo positives and one JoinFreeModules negative (`research/verifypn-frontier.json`). VerifyPN subsumes the observed causal success set on this run. This contradicts any claim of broad current superiority to strong competitors.

A clean, original-input five-property diagnostic with two repetitions (`results/causal-primal-diagnostic`) reproduced all three known sparse-count-plan CAN witnesses in both repetitions. Causal standalone, causal portfolio, sparse-dual portfolio, token-cut and bounded-token-cut all remained unknown on these five queries. The two Echo positives remained unknown for every native method tested. This is an intentionally selected development diagnostic, not held-out evidence.

The causal logs provide a stronger explanation than the earlier scheduling hypothesis: every missing CAN witness branch stopped at 97 arithmetic nodes, 49 integer models and 49 causal cuts. Its 48-level refinement cutoff truncated the witness-discovery path. Increasing the cutoff to 96 (`results/solver-causal-depth96`) made standalone causal solve all three cases twice; portfolio causal solved two consistently and RC15 in only one repetition. A generated 65-place catalyst chain now has a replayed witness; the existing cap/unsupported-branch/finite-net differential tests remain passing.

A second revision keeps the root dual query first, but on a refined node seeks an integer model before a dual refutation. An exactly checked integer model establishes feasibility of the current relaxation, making a separate dual solve unnecessary. If no bounded candidate is found, the unrestricted system still needs an exact Farkas refutation before a negative answer. No candidate bound enters the proof system. Frozen revision: `results/solver-causal-primal-first`; 13 causal tests and all-target clippy pass. Its three-case two-repeat diagnostic again solves all three standalone, with portfolio RC15 still unstable. Do not claim this second change fixes the remaining allocation issue or gives a broad performance gain.

A paired all-development original-input run is now measuring frozen old versus frozen revised causal portfolios and VerifyPN. This is an actual portfolio comparison, not a union of standalone successes. Keep the existing default portfolio-v2 and evaluation families unchanged while assessing it.

## Complete paired development comparison

`results/publication-causal-primal-first/REPORT.md` completes all 256 development properties at 5 seconds with original input, rotated ordering and 2 GiB sampled RSS: old causal 228, revised causal 238, trace-enabled VerifyPN 251. The revision adds nine CAN020 positives and one Echo positive with zero losses or definitive disagreements in this pass. Exact query lists are in `research/causal-primal-first-comparison.json`. Native answers remain independently checked. This is a single shared-host pass, and the competitor trace restriction is material; unrestricted VerifyPN must be measured separately.
