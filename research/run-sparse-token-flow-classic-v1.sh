#!/bin/sh
set -eu
cd /Users/julesjacobs/git/git/pvass
vendor/venv/bin/python -u scripts/benchmark_smpt_classic.py \
 --corpus benchmarks/smpt-classic --binary results/solver-sparse-token-flow-v1/vass-reach \
 --native-tool before-cut token-cut results/solver-capacity-direct-v1/vass-reach \
 --native-tool after-cut token-cut results/solver-sparse-token-flow-v1/vass-reach \
 --native-tool before-bounded bounded-token-cut results/solver-capacity-direct-v1/vass-reach \
 --native-tool after-bounded bounded-token-cut results/solver-sparse-token-flow-v1/vass-reach \
 --methods before-cut after-cut before-bounded after-bounded \
 --rust-original --bounded-validation --validation-seconds 30 --validation-memory-mib 2048 \
 --track-resources --memory-mib 2048 --outer-grace 0 --max-states 2000000 \
 --order-seed 20261007 --output results/sparse-token-flow-classic-v1 --seconds 2 --repeat 1
