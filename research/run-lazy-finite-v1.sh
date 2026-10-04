#!/bin/sh
set -eu
cd /Users/julesjacobs/git/git/pvass
vendor/venv/bin/python -u scripts/benchmark_smpt_classic.py \
 --corpus benchmarks/smpt-classic --binary results/solver-lazy-finite-v1/vass-reach \
 --native-tool finite-before finite-token-cut results/solver-nonzero-control-v1/vass-reach \
 --native-tool finite-after finite-token-cut results/solver-lazy-finite-v1/vass-reach \
 --native-tool lazy lazy-finite-token-cut results/solver-lazy-finite-v1/vass-reach \
 --methods finite-before finite-after lazy \
 --rust-original --bounded-validation --validation-seconds 30 --validation-memory-mib 2048 --validation-response-mib 64 \
 --track-resources --memory-mib 2048 --outer-grace 0 --max-states 2000000 \
 --order-seed 20261013 --output results/lazy-finite-classic-v1 --seconds 2 --repeat 1 > research/lazy-finite-classic-v1.log 2>&1
vendor/venv/bin/python -u scripts/benchmark_smpt_classic.py \
 --corpus benchmarks/hard-development-v2 --binary results/solver-lazy-finite-v1/vass-reach \
 --native-tool finite finite-token-cut results/solver-lazy-finite-v1/vass-reach \
 --native-tool lazy lazy-finite-token-cut results/solver-lazy-finite-v1/vass-reach \
 --native-tool focused portfolio-focused results/solver-lazy-finite-v1/vass-reach \
 --methods finite lazy focused \
 --rust-original --bounded-validation --validation-seconds 60 --validation-memory-mib 2048 --validation-response-mib 64 \
 --track-resources --memory-mib 2048 --outer-grace 0 --max-states 2000000 \
 --order-seed 20261014 --output results/lazy-finite-dlc-probe-v1 --seconds 20 --repeat 1 \
 --filter '^DLCflexbar-PT-7b__RC01$' > research/lazy-finite-dlc-probe-v1.log 2>&1
vendor/venv/bin/python -u scripts/benchmark_smpt_classic.py \
 --corpus benchmarks/hard-development-v2 --binary results/solver-lazy-finite-v1/vass-reach \
 --native-tool finite finite-token-cut results/solver-lazy-finite-v1/vass-reach \
 --native-tool lazy lazy-finite-token-cut results/solver-lazy-finite-v1/vass-reach \
 --native-tool focused portfolio-focused results/solver-lazy-finite-v1/vass-reach \
 --methods finite lazy focused \
 --rust-original --bounded-validation --validation-seconds 30 --validation-memory-mib 2048 --validation-response-mib 64 \
 --track-resources --memory-mib 2048 --outer-grace 0 --max-states 2000000 \
 --order-seed 20261015 --output results/lazy-finite-hard-v1 --seconds 2 --repeat 1 > research/lazy-finite-hard-v1.log 2>&1
