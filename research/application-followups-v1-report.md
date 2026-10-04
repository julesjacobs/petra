# Application screen and follow-up audit

The saved follow-up artifacts pass consistency checks. The parent artifact audit remains failed solely because the registered strict policy quarantines definitive answers accompanied by failure flags. Its existing report and all original rows remain unchanged. No verdict disagreements were found.

## Parent coverage

Full denominator: **192 queries / 187 exact ordered-branch representatives**, six families, four methods, 768 rows. These are development results from one five-second repetition.

| Method | Reported definitive /192 | Strict accepted /192 | Reported /187 representatives | Strict /187 representatives |
|---|---:|---:|---:|---:|
| native-focused | 189 | 189 | 184 | 184 |
| native-symbolic | 189 | 189 | 184 | 184 |
| verifypn-default | 190 | 190 | 185 | 185 |
| smpt-full-portable | 142 | 58 | 137 | 55 |

The strict classification is 57 all-methods-definitive, 135 mixed, and **zero unresolved by every method** (54/133/0 for representatives). Thus this expansion does not establish a broadly hard benchmark set. Failure-contaminated SMPT coverage also inflates the mixed category.

## SMPT capability limitation

MiniZinc is missing in 92 saved logs. Of SMPT’s 142 reported definitive rows, 58 have no failure flags, 78 also report missing MiniZinc and a child-process error, and six have a child-process error without a missing-tool flag. Of the 50 unresolved rows, 14 also report missing MiniZinc; all 50 have timeout/nonzero-exit/error flags. These groups retain every row without double counting.

The other recorded exceptions are KeyboardInterrupt, BrokenPipeError, and ConnectionResetError. No other missing executable is identified in these logs; that does not verify every optional backend dependency. A successful sibling method can emit FORMULA while a CP child fails, so the 84 quarantined answers are **not demonstrated false answers**. Neither their reported coverage nor the strict 58/192 count establishes Rust superiority. A full-capability SMPT comparison requires isolated dependency setup and a new registered run; this audit performs neither.

## Sixty-second qualification

All three competitor-only queries were retained from the complete parent matrix. Same frozen native binary, runner snapshots, competitor configurations, one CPU, 2GiB, strict 60-second outer budget, and separately bounded native validation.

| Query | Rust focused | Rust symbolic | SMPT | VerifyPN default |
|---|---|---|---|---|
| CircadianClock-PT-100000__RC12 | counterexample, 0.56s | counterexample, 0.55s | counterexample, 8.33s | counterexample, 1.42s |
| NoC3x3-PT-8B__RC06 | counterexample, 2.47s | counterexample, 2.75s | counterexample, 6.69s | counterexample, 0.79s |
| NoC3x3-PT-8B__RC12 | timeout, 60.08s | timeout, 60.10s | OOM, 17.24s | counterexample, 0.59s |

All three queries are AG properties, so `reachable` means a counterexample and property truth false. Native definitive answers have saved independently checking witness responses; competitor answers remain tool-reported. Coverage is 2/3 for each Rust configuration and SMPT, 3/3 for default VerifyPN. NoC3x3 RC12 remains a Rust gap, though easy for default VerifyPN. These one-run times are observations, not stable speedup estimates.

The v1 follow-up failed in input preflight because `property.xml` was not relocated. Its manifest, plan, traceback and empty output directory remain. No solver rows were produced. The v2 manifest relocates every top-level artifact path paired with a hash; the auditor verifies the corrected paths and unchanged source identities.

## Separate budget diagnostic and trace attempt

The six profiled runs use a **two-second outer grace** and cannot replace strict-screen timing. NoC3x3 RC06 was unresolved with a five-second internal budget: its two focused phases stopped after 0.70s and 0.75s. With a 60-second budget, its first focused phase found a checked witness in 1.65s; total observed wall time was 2.39s. CircadianClock RC12 likewise changed from unresolved at five seconds to a checked witness in 0.56s total at a 60-second budget. Its first focused phase increased from 0.24s before timeout to 0.40s before success.

These observations support budget-dependent scheduling and insufficient phase allocation as a concrete issue to investigate. Assigned per-branch budgets are not explicitly logged, and no scheduling fix was tested by this audit. NoC3x3 RC12 remained unresolved at both budgets; its 60-second focused phase ran 35.55s.

The separate VerifyPN `--trace` attempt timed out after 60.19s without FORMULA output or a replayed witness. Its log explicitly says trace mode disables H/J/R/S/Q reductions. This is witness-extraction capability evidence, not a substitute for default VerifyPN’s 0.59s result.

## Reproduction and limits

Run locally, without solvers or network access:

```sh
python3 research/audit-application-followups-v1.py
```

Output: `research/application-followups-v1-verification.json`. It retains all 12 qualification rows, six diagnostic rows/profiles, the trace outcome, failures, per-family parent coverage, identities and evidence hashes. The audit checks registered input/native binary bytes, frozen runner snapshots, commands, saved validator responses, FORMULA output, raw perf/systemd sidecars, profile/launcher correspondence, relocation and full selection provenance. Remote tool hashes remain environment-reported; proofs and witnesses were not replayed again. The parent artifact audit is a checked input, including its preserved failure status.

CPU affinity does not establish exclusive isolation. Instruction counts do not remove timeout censorship or contention. Reserved evaluation families remain untouched.
