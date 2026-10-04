#!/bin/sh
set -eu
cd /Users/julesjacobs/git/git/pvass
vendor/venv/bin/python -u scripts/benchmark_smpt_classic.py \
 --corpus benchmarks/smpt-classic --binary results/solver-finite-token-flow-v1/vass-reach \
 --native-tool before-bounded bounded-token-cut results/solver-sparse-token-flow-v1/vass-reach \
 --native-tool after-bounded bounded-token-cut results/solver-finite-token-flow-v1/vass-reach \
 --native-tool finite finite-token-cut results/solver-finite-token-flow-v1/vass-reach \
 --methods before-bounded after-bounded finite \
 --rust-original --bounded-validation --validation-seconds 30 --validation-memory-mib 2048 --validation-response-mib 64 \
 --track-resources --memory-mib 2048 --outer-grace 0 --max-states 2000000 \
 --order-seed 20261008 --output results/finite-token-cut-classic-v1 --seconds 2 --repeat 1
