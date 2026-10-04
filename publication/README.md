# Research archive

Git contains the solver, scripts, tests, patched Varisat source, test inputs, research documents, and experiment summaries. The release archives preserve the complete benchmark inputs, raw results, proofs, failed runs, frozen source snapshots, binaries, and third-party tools. Their original paths and bytes are retained. Each archive has a compressed per-file inventory with SHA-256 hashes; `artifacts.json` records the archive hashes and counts.

Download and restore the evidence from the repository root:

```sh
gh release download research-2026-10-04 --repo julesjacobs/petra --dir ../petra-artifacts
(cd ../petra-artifacts && shasum -a 256 -c SHA256SUMS)
for archive in ../petra-artifacts/petra-*.tar.zst; do
  zstd -dc "$archive" | tar -xf -
done
```

The archives omit compiler caches, Git metadata, Python bytecode, and the local Python virtual environment. They retain the pinned solver, SER, VerifyPN, and Z3 executables separately. Three screenshots containing unrelated private chat titles are excluded; their local originals are unchanged. Some historical scripts record absolute paths and platform-specific dependencies, so restoring the files does not by itself reproduce their original execution environment. Third-party code and tools retain their existing license notices.

For tests from a fresh clone, create the Python environment and install its dependencies before running Cargo:

```sh
python3 -m venv vendor/venv
vendor/venv/bin/pip install -r scripts/requirements.txt
cargo test --locked
```

The test inputs are included in Git; downloading the full research archive is unnecessary for the normal test suite. The command-line executable retains the name `vass-reach` used by the experiment scripts.
