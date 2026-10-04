#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if ! test -f vendor/SerializabilityChecker/src/raw_export.rs; then
  patch -d vendor/SerializabilityChecker -p1 < scripts/ser-raw-export.patch
fi
if [ -z "${ISL_PREFIX:-}" ]; then
  if command -v brew >/dev/null; then
    ISL_PREFIX=$(brew --prefix isl)
  else
    ISL_PREFIX=/usr
  fi
  export ISL_PREFIX
fi
cargo build --release --locked --manifest-path vendor/SerializabilityChecker/Cargo.toml
