#!/bin/sh
set -eu
cd /Users/julesjacobs/git/git/pvass
unset VASS_RELAXED_PROFILE VASS_PORTFOLIO_PROFILE
vendor/venv/bin/python -u scripts/benchmark_smpt_classic.py --corpus benchmarks/candidate-challenges-v1 --binary results/solver-target-stubborn-v1/vass-reach --native-tool before portfolio-focused results/solver-target-stubborn-v1/vass-reach --native-tool after portfolio-target-stubborn results/solver-target-stubborn-v1/vass-reach --methods before after --rust-original --bounded-validation --validation-seconds 30 --validation-memory-mib 2048 --validation-response-mib 64 --track-resources --memory-mib 2048 --outer-grace 0 --max-states 2000000 --order-seed 20261025 --output results/target-stubborn-screen-v1 --seconds 5 --repeat 1 > research/target-stubborn-screen-v1.log 2>&1
