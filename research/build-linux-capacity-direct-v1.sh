#!/bin/sh
set -eu
cd /home/jules/experiments/pvass-publication
test ! -e results/linux-solver-capacity-direct-v1
mkdir -p build/capacity-direct-v1 results/linux-solver-capacity-direct-v1
tar -xzf results/solver-capacity-direct-v1/source.tar.gz -C build/capacity-direct-v1
/home/jules/.cargo/bin/cargo +1.97.1 build --release --locked --manifest-path build/capacity-direct-v1/Cargo.toml
cp build/capacity-direct-v1/target/release/vass-reach results/linux-solver-capacity-direct-v1/vass-reach
cp results/solver-capacity-direct-v1/source.tar.gz results/linux-solver-capacity-direct-v1/source.tar.gz
cp results/solver-capacity-direct-v1/without-capacity results/linux-solver-capacity-direct-v1/without-capacity
sha256sum results/linux-solver-capacity-direct-v1/vass-reach results/linux-solver-capacity-direct-v1/source.tar.gz results/linux-solver-capacity-direct-v1/without-capacity > results/linux-solver-capacity-direct-v1/SHA256SUMS
cat results/linux-solver-capacity-direct-v1/SHA256SUMS
