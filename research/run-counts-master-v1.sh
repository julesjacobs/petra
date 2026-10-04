#!/bin/sh
set -eu
cd /Users/julesjacobs/git/git/pvass
vendor/venv/bin/python -u scripts/benchmark_smpt_classic.py \
 --corpus benchmarks/hard-development-v2 --binary results/solver-counts-master-v1/vass-reach \
 --native-tool lazy-before lazy-finite-token-cut results/solver-lazy-finite-v1/vass-reach \
 --native-tool lazy-after lazy-finite-token-cut results/solver-counts-master-v1/vass-reach \
 --native-tool focused portfolio-focused results/solver-counts-master-v1/vass-reach \
 --methods lazy-before lazy-after focused \
 --rust-original --bounded-validation --validation-seconds 60 --validation-memory-mib 2048 --validation-response-mib 64 \
 --track-resources --memory-mib 2048 --outer-grace 0 --max-states 2000000 \
 --order-seed 20261016 --output results/counts-master-dlc-probe-v1 --seconds 20 --repeat 1 \
 --filter '^DLCflexbar-PT-7b__RC01$' > research/counts-master-dlc-probe-v1.log 2>&1
vendor/venv/bin/python -u scripts/benchmark_smpt_classic.py \
 --corpus benchmarks/smpt-classic --binary results/solver-counts-master-v1/vass-reach \
 --native-tool finite-before finite-token-cut results/solver-nonzero-control-v1/vass-reach \
 --native-tool finite-after finite-token-cut results/solver-counts-master-v1/vass-reach \
 --native-tool lazy-before lazy-finite-token-cut results/solver-lazy-finite-v1/vass-reach \
 --native-tool lazy-after lazy-finite-token-cut results/solver-counts-master-v1/vass-reach \
 --methods finite-before finite-after lazy-before lazy-after \
 --rust-original --bounded-validation --validation-seconds 30 --validation-memory-mib 2048 --validation-response-mib 64 \
 --track-resources --memory-mib 2048 --outer-grace 0 --max-states 2000000 \
 --order-seed 20261017 --output results/counts-master-classic-v1 --seconds 2 --repeat 1 > research/counts-master-classic-v1.log 2>&1
vendor/venv/bin/python -u scripts/benchmark_smpt_classic.py \
 --corpus benchmarks/hard-development-v2 --binary results/solver-counts-master-v1/vass-reach \
 --native-tool lazy-before lazy-finite-token-cut results/solver-lazy-finite-v1/vass-reach \
 --native-tool lazy-after lazy-finite-token-cut results/solver-counts-master-v1/vass-reach \
 --native-tool focused portfolio-focused results/solver-counts-master-v1/vass-reach \
 --methods lazy-before lazy-after focused \
 --rust-original --bounded-validation --validation-seconds 30 --validation-memory-mib 2048 --validation-response-mib 64 \
 --track-resources --memory-mib 2048 --outer-grace 0 --max-states 2000000 \
 --order-seed 20261018 --output results/counts-master-hard-v1 --seconds 2 --repeat 1 > research/counts-master-hard-v1.log 2>&1
vendor/venv/bin/python -u scripts/benchmark_smpt_classic.py \
 --corpus benchmarks/hard-development-v2 --binary results/solver-counts-master-v1/vass-reach \
 --native-tool focused-relevant portfolio-focused results/solver-relevant-finite-v1/vass-reach \
 --native-tool focused-lazy portfolio-focused results/solver-lazy-finite-v1/vass-reach \
 --native-tool focused-counts portfolio-focused results/solver-counts-master-v1/vass-reach \
 --methods focused-relevant focused-lazy focused-counts \
 --rust-original --bounded-validation --validation-seconds 30 --validation-memory-mib 2048 --validation-response-mib 64 \
 --track-resources --memory-mib 2048 --outer-grace 0 --max-states 2000000 \
 --order-seed 20261019 --output results/counts-master-focused-repeat-v1 --seconds 2 --repeat 3 \
 --filter '^DLCflexbar-PT-7b__RC15$' > research/counts-master-focused-repeat-v1.log 2>&1
