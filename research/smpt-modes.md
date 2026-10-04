# SMPT modes on the classical suites

The earlier 16/37 result used only `STATE-EQUATION BMC`. It does not measure SMPT's full capabilities. The installed version also supports induction, k-induction, PDR for coverability, PDR for general reachability, and saturated PDR. K-induction automatically enables BMC. Selected methods run concurrently inside SMPT, while benchmark processes run sequentially.

All runs below use the same 37 original TACAS 2022 properties, two-second internal budgets and three-second SMPT outer limits. The native engine has its previously documented branch allocation and termination allowance. These are wall-time comparisons; the SMPT portfolio can use multiple CPU cores. No net reductions are enabled. The installed SMPT comes from the SER artifact; these findings do not establish behavior of other SMPT versions.

## Mode comparison

| SMPT configuration | Definitive verdicts | Demonstrably wrong verdicts |
|---|---:|---:|
| State equation + BMC | 16/37 | 0 observed |
| Induction | 1/37 | 0 observed |
| K-induction + automatic BMC | 2/37 | 0 observed |
| PDR-REACH | 21/37 | 0 observed |
| PDR-REACH-SATURATED | 27/37 | 1 |
| Combined available portfolio | 35/37 | 1 |

This is one run per configuration, not repeated coverage. Native Rust returned 27/37 independently checked definitive answers in the same run. The SMPT counts are reported verdicts, not verified solves: external proofs have not been independently checked. The combined portfolio enables state equation, BMC, induction, k-induction, PDR-COV, PDR-REACH, and PDR-REACH-SATURATED.

PDR-COV is inapplicable to all 37 targets according to this SMPT version's monotonicity test. Its 37 unknowns in the raw table are not failed coverability searches. `pdr-cov-applicability.json` records this check using SMPT's own parser. WALK needs the absent TINA `walk` tool; automatic reduction and enumeration need absent `reduce`/`tina`. SMT and CP are selected only for fully reduced nets, so enabling them on these unreduced inputs would not test those methods. MiniZinc is installed, but the needed reduced nets are not available.

## Contradicted saturated-PDR result

`Performance/NTest/3u` asks for `A=10` and `C=10`. The original PNML starts at `(A,B,C)=(0,1,0)` and contains:

- `t1`: consumes one B and produces two B plus one C.
- `b`: consumes one B and produces one A.

Thus `t1; b` takes `(k,1,k)` to `(k+1,1,k+1)`. Ten repetitions give `(10,1,10)`, satisfying the original XML target. This 20-step witness was replayed against both native JSON and the original PNML; SMPT's parsed initial marking and transition vectors agree with those inputs.

Nevertheless, `PDR-REACH-SATURATED` returned `FORMULA Marking FALSE`, and the combined portfolio also returned FALSE. The exact root cause has not been established. This is a counterexample to those particular results, not a claim that all PDR implementations or all of SMPT are unsound.

A [three-run focused reproduction](../results/smpt-saturation-repro/REPORT.md) returned FALSE, TRUE, FALSE from saturated PDR on this same input. Rust returned the checked reachable witness in all three runs. The saturated-PDR result is therefore both contradicted in some runs and unstable across runs.

See [raw mode results](../results/smpt-modes/REPORT.md), [original-PNML witness](../results/smpt-modes/3u-original-witness.json), and the per-mode logs and exported proofs alongside them. The benchmark runner exits nonzero on this definitive disagreement. The exact runner version for that run is saved in the results directory and its hash is recorded.

## Reproduce

```sh
python3 scripts/benchmark_smpt_classic.py --methods \
  portfolio-next smpt smpt-induction smpt-k-induction smpt-pdr-cov \
  smpt-pdr-reach smpt-pdr-saturated smpt-portfolio \
  --output results/smpt-modes
python3 scripts/benchmark_smpt_classic.py --methods \
  portfolio-next smpt-portfolio-unsaturated --repeat 3 \
  --output results/smpt-unsaturated
```

`smpt-portfolio-unsaturated` excludes saturated PDR while keeping the other available methods. It is provided to measure coverage separately from the configuration that produced the contradicted answer; absence of a discovered conflict does not independently validate its answers.

## Portfolio without saturation

Across three repetitions, `smpt-portfolio-unsaturated` returned 28/37 definitive answers each time, versus 27/37 for Rust. There were no errors, unstable verdicts, or definitive disagreements. All definitive native answers were independently checked; SMPT answers remain externally reported results. See [the repeated comparison](../results/smpt-unsaturated/REPORT.md).

Rust uniquely solves NTest/3u, NTest/5pi, TokenTank/PGCD-50, and TokenTank/PGCD-500. The unsaturated SMPT portfolio uniquely returns definitive answers for NTest/CryptoMiner, NTest/w2, TokenTank/CryptoMiner-500, TokenTank/CryptoMiner-10000, and Expressiveness/CryptoMiner. Their combined coverage is 32/37.

Consequently, the earlier 27-versus-16 comparison does not establish that Rust beats a stronger SMPT configuration. The available unsaturated portfolio has slightly greater coverage at this budget, and the broader saturated portfolio reports much greater coverage but includes a concrete false unreachability verdict.
