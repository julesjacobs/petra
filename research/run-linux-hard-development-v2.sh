#!/bin/sh
# Run only after the current Linux measurement has terminated and inputs have been deployed.
set -eu
cd /home/jules/experiments/pvass-publication
vendor/venv/bin/python -u scripts/benchmark_smpt_classic.py \
  --corpus benchmarks/hard-development-v2 \
  --binary results/linux-solver-capacity-direct-v1/vass-reach \
  --native-tool native-focused portfolio-focused results/linux-solver-capacity-direct-v1/vass-reach \
  --native-tool native-symbolic portfolio-symbolic results/linux-solver-capacity-direct-v1/vass-reach \
  --methods native-focused native-symbolic verifypn-default smpt-full-portable \
  --rust-original --smpt-original --bounded-validation \
  --validation-seconds 60 --validation-memory-mib 2048 \
  --linux-cpus 8 --perf --memory-mib 2048 --max-states 2000000 --outer-grace 0 \
  --smpt-root vendor/SMPT-portable --smpt-python vendor/venv/bin/python \
  --tool-bin vendor/tina-linux/tina-4.0.0/bin --tool-bin vendor/4ti2-install/bin \
  --verifypn-binary vendor/verifypn/build-release/verifypn/bin/verifypn-linux64 \
  --order-seed 20261006 --output results/linux-hard-development-v2 --seconds 60 --repeat 1
