#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if ! test -f vendor/SerializabilityChecker/src/raw_export.rs; then
  patch -d vendor/SerializabilityChecker -p1 < scripts/ser-raw-export.patch
fi
if ! grep -q 'pub static AUTOMATON:' vendor/SerializabilityChecker/src/raw_export.rs; then
  patch -d vendor/SerializabilityChecker -p1 < scripts/ser-raw-automaton-export.patch
fi
exec sh scripts/setup-raw.sh
