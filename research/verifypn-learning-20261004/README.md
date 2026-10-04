# Learning from VerifyPN: early sparse linear refutation

This iteration brings linear refutation ahead of witness search in `portfolio-excess`. VerifyPN's saved successful logs for ASLink-PT-05b RC12 and Railroad-PT-100 RC09 report query simplification before search. Our standalone sparse state-equation engine also proves those original properties, with independently checked certificates, but the previous default reaches its linear reasoning too late.

## Solver changes

After the initial-marking and grouped-excess checks, the portfolio attempts sparse state-equation refutation with one fifth of the remaining branch budget, capped at 250 ms, and at most 200,000 construction work units. The construction limit counts visited places, transitions, arcs, target coefficients and target-incidence products. It avoids the old estimate that multiplied every arc by the number of target rows. The existing estimate remains in older portfolio stages.

For the necessary state-equation system `Ax >= b`, `x >= 0`, the LP proposes nonnegative multipliers `y` with `Aᵀy <= 0` and `(b/scale)ᵀy >= 1`, where `scale = max(1, max |b_i|)`. Its objective is zero. The previous LP maximized `bᵀy` subject to a dense normalization `sum(y) = 1`. The new LP begins at zero with only the contradiction constraint violated, and that constraint mentions only rows with nonzero bounds. Multipliers can exceed one, so rational reconstruction retains their integer parts.

Every accepted proposal still passes the existing arbitrary-precision rational checker. The proof format remains `sparse-farkas-v1`; the independent Python checker and original-input translation are unchanged. Failure, numerical uncertainty, construction exhaustion and deadline exhaustion continue to the existing search portfolio. The 250 ms LP slice is advisory: microlp can overrun it; the external five-second property limit remains authoritative.

Railroad's second counterexample branch requires three tokens in one place belonging to a conserved group whose initial total is one. A linear invariant refutes it. Existing 0/1 capacity discovery misses this group because its structural hint is invalid and its fallback only follows transitions with a single input. The new linear step discovers a valid certificate from the original incidence matrix.

## Evidence and retained attempts

- `baseline/`: preserved release binary and source before any solver edit; binary SHA-256 `0f591ec86df357cac0ce175d26a9a77d59a69cc4bc51ec9bfe82a6543971b22e`.
- `lp-diagnostic-plan.json`: frozen original-input diagnostic of the pre-existing standalone engines. Sparse LP refutes Railroad RC09 and ASLink 05b RC12; every definitive result was independently checked. Host contention makes timings diagnostic.
- `remaining-lp-diagnostic-plan.json`: four other previous unknowns; standalone linear reasoning does not solve them as whole properties.
- `diagnostic-early-lp/`: first candidate, seven selected properties, one completed audited repetition. No repeated or full-corpus claim.
- `full/`: 90 rows retained; integrity checking stopped the run when review edits changed the harness. It is incomplete.
- `full-v2/`: first candidate with a two-million-unit construction cap. Intentionally stopped after large RERS LPs overran their slices and displaced successful witness search. The stop reason, partial rows and terminal receipt are retained.
- `diagnostic-bounded-lp/`: revised 200,000-unit cap, checking both observed RERS regressions and both target proof cases in two paired repetitions.

All campaigns use original PNML/XML inputs, a five-second whole-property limit, two million search states, buffer agglomeration, and separately bounded independent validation. Full comparisons retain all 368 development properties and 366 ordered-branch representatives. Reserved evaluation families remain untouched. Unrelated host load is sampled continuously; contended runs do not support speed claims.

`all-tests.log` records 625 passing Rust tests, with two ignored. `early-linear-cli-tests.log` adds a passing original-input CLI test for the new early-proof path: weighted conservation, two branches, both EF and AG polarity, and independent Python proof checking. Earlier failed command/compilation logs are preserved. Optimized builds and measurements run sequentially.

VerifyPN supplies the scheduling motivation. Sparse state equations and Farkas certificates were already implemented here; no algorithmic novelty is claimed.

## Completed full comparison

The revised candidate solves **364/368** in both paired repetitions; the preserved baseline solves **363/368** in both. The same Railroad-PT-100 RC09 gain repeats, with **zero losses**. All **1,454 definitive answers** were independently checked; there are no definitive disagreements. The ordered-branch representative view is 362/366 versus 361/366. See [the full report](full-v3/REPORT.md), [detailed results](full-v3/summary.json), and [analysis receipt](full-v3/analysis-receipt.json).

The four remaining original properties are RERS17pb114-PT-5 RC12, ASLink-PT-05b RC06, ASLink-PT-10b RC05, and ASLink-PT-10b RC07. They remain in every denominator.

Observed aggregate solver time was 85.28/84.82 seconds for the candidate versus 179.41/178.77 seconds for the baseline across the two repeats. Checking time was 158.83/157.82 versus 171.26/170.63 seconds, charged separately. These are descriptive totals: host load ranged from 10.28 to 26.02 on 16 logical CPUs, with observed utilization reaching 89%. No idle-host speedup or held-out generalization is established.

`full-v3` preserves all 1,472 invocations. Both per-repeat audits pass. The original `audit.py all` entry point compared deserialized duplicate-group lists with in-memory tuples and therefore rejected an otherwise identical prior audit receipt. The new `summarize.py` normalizes the freshly recomputed result through JSON before comparing it to saved receipts, then calls the frozen summarizer. No admission rule, source pin, timing, host policy or measurement changed. The analysis receipt records this correction and hashes its sources and outputs.

After measurement, formatting collapsed only the `state_equation_bounded` signature onto one line. The final release receipt records this source-only formatting difference from the measured snapshot. `cargo clippy --all-targets -- -D warnings` passed; the vendored Varisat dependency still emits its existing warnings. The touched files pass the formatter check.
