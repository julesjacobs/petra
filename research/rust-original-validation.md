# Rust original-input benchmark adapter

Implemented 2026-09-27. `scripts/benchmark_smpt_classic.py --rust-original` invokes the Rust PNML/XML frontend directly. The existing default canonical-JSON mode and `--native-original` Python frontend remain available; the two original-input switches are mutually exclusive.

The timed command includes process startup, PNML/XML reads, parsing, DNF construction, in-process branch scheduling, solving, and output serialization. The adapter accepts no definitive result after the configured whole-property wall deadline, even if an outer shutdown grace allows the process to exit successfully. The Rust `deadline_exceeded` flag also forces an unknown result.

Independent verification always runs afterward in the existing separately bounded Python worker. It is excluded from solver timing and has its own wall, memory, and response-size limits. `rust_original_validation.py` requires the `original-property-v1` schema, exact property ID/polarity/branch count, consistent aggregate verdict/truth, and a contiguous attempted-branch prefix. It hashes original PNML/XML and canonical files, independently translates the original input with the Python frontend, and compares every canonical branch. Arc tuples produced by the importer are normalized to JSON lists before comparison.

Each embedded definitive outcome is checked against that canonical original branch with `benchmark.verify`. Unsupported negative certificates become unknown. Unreachability requires every branch to have a checked negative result; zero branches require independent confirmation of the empty disjunction. EF/AG truth is derived only after checked aggregation. Input identity is checked again after verification. The checker refuses optimized Python execution because the existing certificate checkers use assertions.

## Verified checks

- New adapter/checker suite: 14 tests passed (`research/rust-original-validation-tests.log`). Includes original witness replay, threshold/Farkas negatives, EF/AG truth, exact property selection, empty formulas, forged metadata/proofs, partial coverage, input mutation, deadline preservation, unsupported negative downgrade, the bounded worker path, mixed frontend dispatch, and method selection validation.
- Existing Python frontend, bounded-validation, and importer regression suites: 52 tests passed (`research/rust-original-python-regressions.log`).

These checks establish the exercised adapter behavior; they are not a performance measurement or a claim that every certificate family has been tested through the new frontend.

## Development command

After a release binary with `--pnml` support has been built and frozen, and when no competing local measurement is active:

```sh
vendor/venv/bin/python scripts/benchmark_smpt_classic.py \
  --corpus benchmarks/mcc-publication-development \
  --output results/rust-original-development-v1 \
  --binary /absolute/path/to/frozen/vass-reach \
  --methods portfolio-local --rust-original \
  --seconds 5 --repeat 1 --outer-grace 0 \
  --track-resources --memory-mib 2048 \
  --validation-seconds 30 --validation-memory-mib 2048
```

The placeholder binary must be replaced with the frozen candidate path. This command has not been run. Compare frontend modes as separately identified configurations; in-process advisory branch shares differ from the Python wrapper's per-branch subprocess enforcement. Existing frozen results are unchanged.

## Paired frontend comparison

`--rust-original-method LABEL` is repeatable and overrides the input mode only for selected native labels. Combine it with `--native-original` to keep other native methods on the Python frontend. Every label must appear in `--methods` and must not be a SMPT or VerifyPN configuration. Selecting any Rust frontend forces bounded independent validation. Global `--rust-original` still selects Rust for every native method and remains incompatible with global `--native-original`.

For the same frozen binary/engine on both frontend paths, plus VerifyPN:

```sh
vendor/venv/bin/python scripts/benchmark_smpt_classic.py \
  --corpus benchmarks/mcc-publication-development \
  --output results/paired-frontends-development-v1 \
  --binary /absolute/path/to/frozen/vass-reach \
  --native-tool candidate-python portfolio-local /absolute/path/to/frozen/vass-reach \
  --native-tool candidate-rust portfolio-local /absolute/path/to/frozen/vass-reach \
  --methods candidate-python candidate-rust verifypn-default \
  --native-original --rust-original-method candidate-rust \
  --seconds 5 --repeat 3 --order-seed 20260927 --outer-grace 0 \
  --track-resources --memory-mib 2048
```

The default VerifyPN binary path must exist. This command has not been run. To add the older binary through Python, append `frozen-v2` to `--methods` and pass its path with `--baseline-binary`; do not select it with `--rust-original-method`.

Environment metadata records `rust_original_methods` and `method_input_scope` for every selected method. Each result row records `input_mode`, including external methods and unexecuted collection slots. The selected Rust checker source is hashed whenever either Rust selection option is used. Original PNML/XML hashes are preflight checked in either mode.
