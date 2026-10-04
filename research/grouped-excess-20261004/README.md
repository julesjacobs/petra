# Grouped-excess comparison

Completed and audited: the candidate solves 337/368 properties versus 323/368,
with fourteen gains and no losses. See [results](RESULTS.md). The protocol compares
`portfolio-excess` with the frozen `portfolio-reduced` baseline, both with buffer
agglomeration, at strict five-second original-PNML/XML deadlines.

The completed command sequence was:

```sh
vendor/venv/bin/python research/grouped-excess-20261004/run.py freeze --candidate /absolute/path/to/frozen/vass-reach
vendor/venv/bin/python research/grouped-excess-20261004/run.py run diagnostic
vendor/venv/bin/python research/grouped-excess-20261004/run.py audit diagnostic
vendor/venv/bin/python research/grouped-excess-20261004/run.py run full
vendor/venv/bin/python research/grouped-excess-20261004/run.py audit full
```

The diagnostic retains all 32 DNAwalker properties (64 runs). The full screen retains all 176 old and 192 new properties (736 runs), reporting both corpora and the pooled 368 slots / 366 ordered-branch representatives. Diagnostic observations are not pooled into the full screen. Query order is deterministic and the candidate runs first exactly half the time in each full corpus.

Freeze copies both binaries and every Python runner/checker script, records all original/canonical input hashes, and fixes the entire schedule. The harness uses the existing `benchmark_smpt_classic.rust_original` runner and independent original-input validator. Every definitive answer must pass bounded independent validation outside solver timing. Validation receives 60 seconds, sampled 2 GiB, a 64 MiB response limit and 200 million DAG-check work units.

The Mac runner enforces a strict outer deadline and terminates the process tree when sampled RSS exceeds 2 GiB. RSS sampling is not a cgroup guarantee. Workload checks prohibit overlapping local builds or timed solver runs. Remote Linux is untouched.

Preparation and freeze do not build or launch a solver. Full execution requires a passing diagnostic audit. Results, terminal receipts, failed outcomes and per-stage audits are retained without overwrite. A changed candidate requires a new campaign directory. This is one local development screen; it supports no stable-speed or held-out generalization claim.
