set -eu
cd /home/jules/experiments/pvass-publication
test ! -e results/linux-solver-shared-relevance-schemas-v1
mkdir -p build/shared-relevance-schemas-v1 results/linux-solver-shared-relevance-schemas-v1
tar -xzf results/solver-shared-relevance-schemas-v1/source.tar.gz -C build/shared-relevance-schemas-v1
/home/jules/.cargo/bin/cargo +1.97.1 build --release --locked --manifest-path build/shared-relevance-schemas-v1/Cargo.toml
cp build/shared-relevance-schemas-v1/target/release/vass-reach results/linux-solver-shared-relevance-schemas-v1/vass-reach
cp results/solver-shared-relevance-schemas-v1/source.tar.gz results/linux-solver-shared-relevance-schemas-v1/source.tar.gz
sha256sum results/linux-solver-shared-relevance-schemas-v1/vass-reach results/linux-solver-shared-relevance-schemas-v1/source.tar.gz > results/linux-solver-shared-relevance-schemas-v1/SHA256SUMS
cat results/linux-solver-shared-relevance-schemas-v1/SHA256SUMS
