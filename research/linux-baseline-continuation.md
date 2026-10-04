# Linux baseline continuation after ENODEV

The initial `results/linux-original-perf-development2` run stopped with 690 recorded invocations after `cgroup.procs` disappeared during sampling (`OSError: ENODEV`). It contains 86 complete original-property groups (4 methods × 2 repetitions), plus two records of the next property. All 86 complete groups are retained regardless of verdict. The partial property and 169 unvisited properties are rerun in full: 1360 invocations.

`scripts/linux_runner.py` now ignores only ENOENT and ENODEV when reading `cgroup.procs`; EACCES/EIO and other errors propagate. Fourteen Linux runner tests passed, including injected ENODEV/ENOENT races and other-error propagation; `research/linux-runner-enodev-tests.log` records the run. No solver or benchmark scheduling behavior changed.

`scripts/linux_benchmark_segments.py resume` imports the unchanged frozen remote benchmark driver, verifies every prior source snapshot, every current source dependency except the narrowly checked runner patch, both frozen Rust binaries, Python frontend, VerifyPN binary, SMPT source, external tool binaries, and all original/canonical input hashes. It uses the prior full property-order indices when rotating method order. Thus skipping retained groups does not reset rotations or shuffle the subset. The six-record prefix tests include incomplete-group replacement, rejected duplicate/missing rows, changed ordering, changed native-original/perf/CPU/memory/frontend/competitor configurations, source mutation, and outcome-dependent selection. Six segment tests passed locally and remotely.

The strict `combine` command requires exact complete continuation coverage, original invocation ordering and source/configuration compatibility. It preserves ordinary top-level environment fields for analysis and adds `segment_configurations`, `segment_provenance`, and a caveat rather than replacing the environment with a wrapper. Raw artifacts remain in their source segments; merged records carry a `segment` path. No actual merged result exists until continuation completes.

Verified preflight: `research/linux-baseline-continuation-preflight.log`. Prior records SHA256: `7e4cd8de361a72d598af68ffa3ad1fac6c99d2549073d40334d9d96b4f58b9b0`. Prior environment SHA256: `75f869081be8a2948ee10091aca202990e7acf485ff541b601a1d94f9718c1c2`.

Continuation command on the Linux workspace:

```
vendor/venv/bin/python scripts/linux_benchmark_segments.py resume \
  --prior results/linux-original-perf-development2 \
  --corpus benchmarks/mcc-publication-development \
  --output results/linux-original-perf-development2-rest \
  --binary results/linux-solver-causal/vass-reach \
  --baseline results/linux-solver-v2/vass-reach
```

After completion:

```
vendor/venv/bin/python scripts/linux_benchmark_segments.py combine \
  --prior results/linux-original-perf-development2 \
  --continuation results/linux-original-perf-development2-rest \
  --manifest benchmarks/mcc-publication-development/manifest.json \
  --output results/linux-original-perf-development2-combined
```

Continuation started after the candidate's separate Linux build completed. Live session handle at launch: `28134`; local stream log `research/linux-original-perf-development2-rest.log`; remote result directory `results/linux-original-perf-development2-rest`. Initial check observed 15/1360 invocations written. Root owns subsequent monitoring. SEGMENT.json SHA256: `4afe3b223604adf0bf4b7b0b2929ea729776e275c882287fd62137ac4be75be1`; patched runner SHA256: `413475025b17beaa5a027c6e3495c8dfb0f4898d5e95a79c0f5fe5ad48db5504`; continuation driver SHA256: `df2f20f52f0c5a2cc8de8f40dcc66c20bd99830774346ae7787ad0bb3c49a498`.
