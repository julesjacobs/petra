#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p vendor research
if [ ! -f vendor/SerializabilityChecker/Cargo.toml ]; then
    archive=$(mktemp -t ser-artifact)
    curl -fL https://zenodo.org/api/records/17253581/files/ser_artifact.zip/content -o "$archive"
    actual=$(shasum -a 256 "$archive" | cut -d ' ' -f 1)
    test "$actual" = d5bdbc52b11470fc7c0d74e06c5fe5a32880db5344c06e204cff42ec5831eeeb
    unzip -q "$archive" -d vendor
    rm "$archive"
fi
python3 -m venv vendor/venv
vendor/venv/bin/pip install -r scripts/requirements.txt
chmod u+x vendor/SerializabilityChecker/smpt_wrapper.sh
if [ -z "${ISL_PREFIX:-}" ] && command -v brew >/dev/null; then
    ISL_PREFIX=$(brew --prefix isl)
    export ISL_PREFIX
fi
cp scripts/ser.Cargo.lock vendor/SerializabilityChecker/Cargo.lock
cargo build --release --locked --manifest-path vendor/SerializabilityChecker/Cargo.toml
cargo build --release --locked
