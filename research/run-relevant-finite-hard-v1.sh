#!/bin/sh
set -eu
cd /Users/julesjacobs/git/git/pvass
vendor/venv/bin/python -u scripts/benchmark_smpt_classic.py \
 --corpus benchmarks/hard-development-v2 --binary results/solver-relevant-finite-v1/vass-reach \
 --native-tool finite-before finite-token-cut results/solver-finite-token-flow-v2/vass-reach \
 --native-tool finite-relevant finite-token-cut results/solver-relevant-finite-v1/vass-reach \
 --native-tool focused portfolio-focused results/solver-relevant-finite-v1/vass-reach \
 --methods finite-before finite-relevant focused \
 --rust-original --bounded-validation --validation-seconds 30 --validation-memory-mib 2048 --validation-response-mib 64 \
 --track-resources --memory-mib 2048 --outer-grace 0 --max-states 2000000 \
 --order-seed 20261010 --output results/relevant-finite-hard-v1 --seconds 2 --repeat 1
