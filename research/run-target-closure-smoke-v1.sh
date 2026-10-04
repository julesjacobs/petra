#!/bin/sh
set -eu
cd /Users/julesjacobs/git/git/pvass
unset VASS_RELAXED_PROFILE VASS_PORTFOLIO_PROFILE
vendor/venv/bin/python -u scripts/benchmark_smpt_classic.py --corpus benchmarks/smpt-classic --binary results/solver-target-stubborn-v1/vass-reach --native-tool before portfolio-target-stubborn results/solver-target-stubborn-v1/vass-reach --native-tool after portfolio-target-stubborn results/solver-target-closure-v1/vass-reach --methods before after --rust-original --bounded-validation --validation-seconds 30 --validation-memory-mib 2048 --validation-response-mib 64 --track-resources --memory-mib 2048 --outer-grace 0 --max-states 2000000 --order-seed 20261028 --output results/target-closure-smoke-v1 --seconds 2 --repeat 1 --filter '^(Performance__NTest__3u|Certificates__Parity)$' > research/target-closure-smoke-v1.log 2>&1
