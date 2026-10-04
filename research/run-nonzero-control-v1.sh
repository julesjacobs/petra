#!/bin/sh
set -eu
cd /Users/julesjacobs/git/git/pvass
vendor/venv/bin/python -u scripts/benchmark_smpt_classic.py \
 --corpus benchmarks/smpt-classic --binary results/solver-nonzero-control-v1/vass-reach \
 --native-tool finite-before finite-token-cut results/solver-relevant-finite-v1/vass-reach \
 --native-tool finite-after finite-token-cut results/solver-nonzero-control-v1/vass-reach \
 --methods finite-before finite-after \
 --rust-original --bounded-validation --validation-seconds 30 --validation-memory-mib 2048 --validation-response-mib 64 \
 --track-resources --memory-mib 2048 --outer-grace 0 --max-states 2000000 \
 --order-seed 20261011 --output results/nonzero-control-classic-v1 --seconds 2 --repeat 1 > research/nonzero-control-classic-v1.log 2>&1
vendor/venv/bin/python -u scripts/benchmark_smpt_classic.py \
 --corpus benchmarks/hard-development-v2 --binary results/solver-nonzero-control-v1/vass-reach \
 --native-tool finite-before finite-token-cut results/solver-relevant-finite-v1/vass-reach \
 --native-tool finite-after finite-token-cut results/solver-nonzero-control-v1/vass-reach \
 --methods finite-before finite-after \
 --rust-original --bounded-validation --validation-seconds 30 --validation-memory-mib 2048 --validation-response-mib 64 \
 --track-resources --memory-mib 2048 --outer-grace 0 --max-states 2000000 \
 --order-seed 20261012 --output results/nonzero-control-hard-v1 --seconds 2 --repeat 1 > research/nonzero-control-hard-v1.log 2>&1
