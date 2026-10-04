# Expanded benchmarks and the frozen Rust portfolio

`portfolio-v2` is the new default. It adds inductive interval partitions and property-directed projections with independently checked certificates, plus projected witnesses that must replay on the original net. The earlier `portfolio-next` remains available.

## Coverage at two seconds

| Corpus | Old Rust | New Rust | Unsaturated SMPT | Repetitions |
|---|---:|---:|---:|---:|
| Classical SMPT, 37 original properties | 27 | **37** | 28 | 3 |
| MCC evaluation, 192 original properties | 175 | **175** | 99 | 1 |
| MCC development, 192 original properties | 140 | **142** | — | 1, separate development runs |
| Previous SER backend, 218 disjuncts | 217 | **217** | — | 1 |

Counts are definitive answers. Every definitive native branch in the final runs passed independent Python witness, arithmetic, structural, interval, projected-closure, or finite-closure verification. No definitive answers disagreed. Classical coverage was stable across all three repetitions. SMPT counts are reported answers; its proofs were not independently checked.

The new solver solves all classical cases, including the ten previously unresolved properties. Evaluation coverage is unchanged: this experiment does **not** show a coverage improvement on unseen MCC families. On development, the net improvement is two: three new TokenRing proofs (`RC00`, `RC04`, `RC05` for `TokenRing-PT-015`) and one lost witness within the time limit (`DatabaseWithMutex-PT-10__RC03`). The old witness remains independently valid; the new answer is unknown, not a contradiction. Development's old count comes from the first expanded-development comparison, while the final new count uses the frozen binary.

The classical set includes two duplicate certificate examples. SER's 218 rows are simplified backend disjuncts, not whole programs; do not add or directly equate those counts with the whole-property corpora. `g2_disjunct_1` remains the single automatic SER unknown, despite its separate manual proof.

## Benchmark expansion

Added **384 original MCC 2021 properties** from 24 P/T instances across 12 families. Nets reach 830 places and 3,616 transitions. The selection contains the first and third published instances per family, and all 16 cardinality properties per instance. All 384 imported successfully from the original PNML/XML, with no net reductions.

Development and evaluation are split by family, 192 properties each. The split was fixed before solver development; the solver was frozen before running evaluation. The larger parameter tier was added after the old solver solved all development properties at the smallest tier, without consulting evaluation results. Initial-target cases are retained: 47 development and 12 evaluation queries are satisfied at the initial marking. The result-selected 52-case development challenge subset is for tuning, not headline coverage.

Archives, source inputs and metadata are retained under `vendor/mcc2021`. URLs and archive SHA-256 hashes are pinned in `benchmarks/mcc-selection.json`; manifests retain original property IDs, polarity, and converted input hashes. Full corpus manifests are in `benchmarks/mcc2021`, `benchmarks/mcc2021-development`, and `benchmarks/mcc2021-evaluation`.

## Limits and evidence

Remaining unknowns: 50 development properties, 17 evaluation properties, and one previous SER backend query. Raw SER queries still use the earlier raw-target engine. These results do not establish a general reachability record or end-to-end serializability performance.

Measurements use sequential cold processes on a shared host. Native branches share a two-second whole-property budget, with an outer termination allowance; SMPT has a two-second internal and three-second outer limit and may run its methods in parallel. Import and independent checking are outside timing. The comparison uses SMPT's available unsaturated portfolio; missing TINA walking/reduction/enumeration modes are not measured. Saturated PDR is excluded because of the previously demonstrated false verdict.

The native code passed 101 Rust tests, including 100 bounded-net differential cases for the new engines, and Clippy with warnings denied. Python checker tests reject forged invariants and projected closures. Source-XML tests cover 38,784 MCC predicate valuations and 37,037 classical predicate valuations. Standalone `--verify` checks passed for both new certificate formats; default raw mode also passed a witness verification smoke check.

Frozen release binary SHA-256: `4abae89f2187ff710a3759accd20acf3f7618582a202ccbc5b4402608554e7b1`. A copy and source snapshot are under `results/solver-v2/`; the previous binary is preserved there as `baseline-vass-reach`.

- [Classical repeated comparison](classic-v2-final/REPORT.md)
- [Untouched-family evaluation](mcc-evaluation-v2/REPORT.md)
- [Frozen development run](mcc-development-frozen/REPORT.md)
- [Earlier expanded-development comparison](mcc-development-v2/REPORT.md)
- [SER regression comparison](ser-v2-final/REPORT.md)
- [Design, selection procedure, and reproduction commands](../research/solver-v2.md)

```sh
./target/release/vass-reach --json problem.json --seconds 2
python3 scripts/benchmark_smpt_classic.py \
  --corpus benchmarks/mcc2021-evaluation \
  --methods portfolio-next portfolio-v2 smpt-portfolio-unsaturated \
  --output results/mcc-evaluation-v2
```
