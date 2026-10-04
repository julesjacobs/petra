# MCC 2021 family-separated benchmark selection

384 original reachability-cardinality properties from 24 ordinary P/T instances across 12 families. The first and third published instances of each family are included, with all 16 properties per model. Development and evaluation contain disjoint families, 192 properties each.

`../mcc-selection.json` records the selection rule, split, archive URLs and SHA-256 hashes. `scripts/collect_mcc.py` downloads and imports them. Original archives, source models and metadata are retained under `vendor/mcc2021/`; the source is [Yann Thierry-Mieg's MCC 2021 repository](https://yanntm.github.io/pnmcc-models-2021/).

`manifest.json` records original property polarity and hashes. Individual `branch-N.json` files are native reachability queries; a reachable branch of an AG property refutes it. Use the whole-property runner to combine branches:

```sh
python3 scripts/benchmark_smpt_classic.py \
  --corpus benchmarks/mcc2021-evaluation \
  --methods portfolio-next portfolio-v2 smpt-portfolio-unsaturated \
  --output results/mcc-evaluation-v2
```

See [design and reproduction details](../../research/solver-v2.md). This is a specified selection, not the complete MCC repository.
