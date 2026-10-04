# Published SMPT benchmark suites

Source: Amat, Dal Zilio, and Hujsa, *Property Directed Reachability for Generalized Petri Nets*, TACAS 2022, [published artifact](https://doi.org/10.5281/zenodo.5863379), linked by the [SMPT repository](https://github.com/nicolasAmat/SMPT).

Downloaded `SMPT_TACAS_2022.zip` (446,015,375 bytes). Its MD5 matches Zenodo's `d676b46e112843aab081a5a3feb6c6de`; the reproduction script pins SHA-256 `738608b17c7e698543cbcca9072aa6050a3e3e891074ec8b596b7fde66dbff48`. The archive is retained under `vendor/smpt-benchmarks/`. Extraction selects the benchmark inputs, their original run scripts and instance lists, the readme, and license. It does not run the artifact's installer or bundled executables. The downloader requires Python 3.11 or newer and curl.

## Included inputs

| Published suite | Original properties |
|---|---:|
| Performance / NTest | 21 |
| Performance / Sara | 3 |
| Performance / TokenTank | 6 |
| Expressiveness | 5 |
| Certificates | 2 |
| Total | 37 |

All published instance lists are included without selection, and all 37 inputs import successfully. Certificate examples repeat the Parity and PGCD expressiveness problems; keep that duplication visible when reporting aggregate results. These small nets (1–8 places and 1–8 transitions) exercise arithmetic and unbounded behavior. TokenTank parameters are 50, 500, and 10,000. This corpus is the paper's published suites, not the full Model Checking Contest repository.

## Conversion

`scripts/smpt_import.py` parses ordinary P/T PNML, preserving initial markings, transition order, weighted pre/post arcs, and read arcs. PNML IDs identify nodes; display names do not. Parallel ordinary arcs are summed. Defaults are zero initial tokens and unit arc weights. Unsupported types, arc extensions, unknown endpoints, and numeric overflow fail explicitly.

MCC XML `EF P` is translated to reachability of P. `AG P` is translated to reachability of a counterexample satisfying not-P. Boolean targets are converted exactly to disjunctive normal form with a branch limit; strict integer inequalities use the appropriate one-unit offset. There is no net reduction, pruning, or target satisfiability preprocessing during import. Process and Murphy each yield two branches, giving 39 backend JSON files for 37 original properties.

`benchmarks/smpt-classic/manifest.json` records original file locations and hashes, property IDs and polarity, and converted file hashes. Each directory contains native `branch-N.json` files and a TINA net/XML pair for SMPT with consistent generated node IDs. Original PNML/XML files remain in `vendor/smpt-benchmarks/tacas2022/Artifact/`. The upstream GPLv3 license is preserved alongside the converted inputs.

## Running

```sh
python3 scripts/setup-smpt-benchmarks.py
python3 scripts/smpt_import.py
python3 scripts/test_smpt_import.py
cargo build --release --locked
./target/release/vass-reach \
  --json benchmarks/smpt-classic/Expressiveness__Parity/branch-0.json \
  --seconds 2
python3 scripts/benchmark_smpt_classic.py --seconds 2 \
  --methods portfolio-next smpt --output results/smpt-classic
```

Use `--filter 'Sara|TokenTank'`, `--methods bfs portfolio-next`, or `--repeat 3` for subsets, native comparisons, or repeated measurements. The SMPT comparison uses the already installed SER artifact version of SMPT with `STATE-EQUATION BMC`, without net reductions; it does not reproduce the original paper's tool configurations or 255/3,600-second budgets. `scripts/setup.sh` supplies that SMPT installation if it is missing.

The benchmark runner reports whole original properties. A reachable branch establishes reachability; unreachability requires every branch to be unreachable. Native branches share the requested budget, divided among remaining branches; a half-second outer termination allowance is used per invocation. SMPT receives `ceil(seconds)` internally and a `seconds+1` outer limit. Process wall times include parsing/startup and exclude independent proof checks. The two budget mechanisms are not identical, so short-budget timing comparisons are exploratory.

`runs.jsonl` records both counterexample reachability and `property_truth`: an unreachable counterexample means an AG property is true. Native witnesses and available certificates are independently checked by the existing Python verifier; any missing certificate is explicitly recorded. SMPT's exported proofs are retained but not independently verified. No external result is used as a ground-truth label. Reports fail the run on definitive disagreements or errors.

Tests cover PNML defaults, weights, parallel/read arcs, malformed/unsupported inputs, strict comparisons, Boolean negation, and property polarity. A separate XML evaluator agrees with the converted targets on the initial marking and 1,000 deterministic sample markings for each of the 37 inputs (37,037 checks); this tests predicate translation, not reachability.

See [the first comparison](../results/smpt-classic/REPORT.md) and [three repeated runs](../results/smpt-classic-repeated/REPORT.md).

At two seconds, all three repetitions returned the same coverage: the native default portfolio solved 27/37 properties (one reachable target, 26 unreachable targets), and the selected SMPT configuration solved 16/37. There were no errors or conflicting definitive answers. Every definitive native branch passed independent witness, arithmetic/structural certificate, or finite-closure checking. These are short-budget results for the stated configurations, not a comparison against SMPT's full portfolio or the original paper's measurements.

The ten native unknowns are NTest/CryptoMiner, NTest/w2, TokenTank/PGCD-10000, TokenTank/CryptoMiner-500, TokenTank/CryptoMiner-10000, and the Expressiveness PGCD, CryptoMiner, Process, and Murphy examples, plus the duplicate Certificates/PGCD example.

**Follow-up:** SMPT's stronger unsaturated portfolio returned 28/37 definitive answers across three repetitions. The original 16/37 baseline understates SMPT's capabilities. Including saturated PDR increased reported coverage but produced a demonstrably wrong verdict. See [the mode comparison](smpt-modes.md).
