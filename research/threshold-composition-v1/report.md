# Supplied signed-threshold proof composition

`results/runner-threshold-v1` freezes the 23-file phase-pair-v2 closure plus `signed_threshold_checker.py`. Only isolated `benchmark.py` dispatch and `benchmark_smpt_classic.py` source recording changed. Both historical phase-pair runners were hash-checked unchanged; the new closure and every archive member were verified. Shared benchmark scripts remain unchanged.

`vendor/venv/bin/python tests/check_threshold_composition.py` passed four tests (`tests-fixed.log`), including five actual bounded Rust original-input validator child processes. Independent PNML/XML translation and all canonical branches are checked. Direct signed-threshold and relevance-wrapped supplied proofs produce checked negative answers; malformed proof arithmetic produces an error; an unsupported proof kind preserves the existing error result; an unknown answer remains unknown and unchecked. Tests also reject malformed unreferenced target rows and a damaged wrapped invariant.

The first test run had incorrect expectations about existing unsupported-proof behavior and the rejection stage for a damaged invariant. The failed log is retained; the checker and runner were unchanged by the test corrections.

This verifies certificate dispatch and composition on supplied synthetic proofs. No solver discovery, benchmarks, Rust builds, or Linux work were performed. Hashes and validation receipt are in `validation.json`.
