# SMPT TACAS 2022 inputs

Generated from the [published artifact](https://doi.org/10.5281/zenodo.5863379) by `scripts/smpt_import.py`. Original inputs are retained under `vendor/smpt-benchmarks/tacas2022/Artifact/`; the archive hash is pinned in `scripts/setup-smpt-benchmarks.py`. See `LICENSE.upstream.txt` for the original license.

`manifest.json` lists all 37 published properties, their source and converted hashes, and their EF/AG polarity. The 39 `branch-N.json` files are native reachability queries; a reachable AG branch refutes the invariant. Use `scripts/benchmark_smpt_classic.py` to combine branches and report original property truth values. Each directory also contains an equivalent TINA/XML pair for SMPT.

The two Certificates inputs duplicate Parity and PGCD from Expressiveness. They remain separate to preserve the published suite lists. See [conversion and reproduction details](../../research/smpt-classic.md).
