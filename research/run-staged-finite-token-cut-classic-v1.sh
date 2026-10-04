#!/bin/sh
set -eu
cd /Users/julesjacobs/git/git/pvass
vendor/venv/bin/python -u scripts/benchmark_smpt_classic.py \
 --corpus benchmarks/smpt-classic --binary results/solver-finite-token-flow-v2/vass-reach \
 --native-tool finite-before finite-token-cut results/solver-finite-token-flow-v1/vass-reach \
 --native-tool finite-after finite-token-cut results/solver-finite-token-flow-v2/vass-reach \
 --native-tool focused portfolio-focused results/solver-finite-token-flow-v2/vass-reach \
 --native-tool symbolic portfolio-symbolic results/solver-finite-token-flow-v2/vass-reach \
 --methods finite-before finite-after focused symbolic \
 --rust-original --bounded-validation --validation-seconds 30 --validation-memory-mib 2048 --validation-response-mib 64 \
 --track-resources --memory-mib 2048 --outer-grace 0 --max-states 2000000 \
 --order-seed 20261009 --output results/staged-finite-token-cut-classic-v1 --seconds 2 --repeat 2
