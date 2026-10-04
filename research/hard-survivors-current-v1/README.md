# Historical survivors with current tools

Prepared locally, not deployed or launched. Wait for Linux session33484 and any
subsequent measurement to be confirmed terminal before deployment or launch.

This registers **all eight original hard-survivors-v1 queries**, including any
that later tools solved: six FastForward random-walk cases and two pigeonhole
cases. The original denominators remain **620 parent queries, 69 screened,
eight selected**. `history.json` preserves the complete original selection audit
and all32historical300-second rows, including failures. No reserved-family inputs
were accessed. Existing PNML/XML and branch identities were verified; the new
manifest only rebases paths and uses existing suite labels for report grouping.

The new plan has32rows at300seconds, one repetition, CPU8, perf, enforced2GiB,
two million states and zero outer grace. Configurations are the same frozen
native focused+buffer and batched+buffer, VerifyPN default, and repaired SMPT
full portable used by the application qualification. Independent native checking
is outside solver timing, bounded at60seconds/2GiB/64MiB response/200M DAG work.
Both positive and negative native answers require successful checking. Competitor
answers remain tool-reported. The historical SMPT failures are not retroactively
repaired by the new dependency configuration.

Print the exact command locally without executing it:

```sh
python3 research/run-hard-survivors-current-v1.py
```

After confirmed idle-host deployment and preflight, launch explicitly on Linux:

```sh
vendor/venv/bin/python research/run-hard-survivors-current-v1.py \
  --launch --terminal-predecessor CONFIRMED_COMPLETED_SESSION_ID
```

The launcher checks registered files, workload absence, output absence and the
MiniZinc repair preflight. Its predecessor argument records an operator-confirmed
session identity; it cannot independently establish session completion. The plan
inherits the complete current-tool identity closure, including prior corpus and
smoke evidence already present remotely. Deploy these new research files plus
their hashed historical evidence and the registered command helper before the
run; do not transfer or develop on Linux during measurement.

After terminal completion and full retrieval, audit with the current general
application auditor (its bytes are registered in the plan):

```sh
python3 research/audit-linux-application-expansion-v1.py \
  --plan research/hard-survivors-current-v1/plan.json \
  --results results/linux-hard-survivors-current-v1 \
  --output research/hard-survivors-current-v1/verification.json
```

Report all32rows and six FastForward/two pigeonhole cases separately, retaining
timeouts, memory limits, checker failures and counter-coverage warnings. This is
an outcome-selected development requalification, not held-out evaluation or a
stable speed study. Parsing, preprocessing, solving and output remain in the
outer deadline; the old FastForward offline conversion remains excluded. For
killed runs without complete phase data, do not attribute the timeout to search
or infer that parsing was negligible. A300-second run can still hit the unchanged
state cap. No automatic survivor filtering or further run is registered.
