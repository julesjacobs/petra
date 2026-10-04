# New development cohort: Linux qualification

Prepared only; remote capability preflight and deployment are pending. No
benchmark, build, or import was performed while preparing this experiment.

The fixed cohort has 176 imported properties and 175 exact ordered-branch
representatives. All nine configurations run every property, one seeded repeat:
1,584 rows. Limits are 5 seconds, CPU8, cgroup 2 GiB and perf counters, original
PNML/XML, with separately bounded 60-second/2-GiB native checking. The three
native controls preserve their earlier Linux binary hashes, engines, compiled
walk defaults, and buffer agglomeration flags. Five SMPT configurations compare
full, compact, PDR, saturated PDR and official MCC scheduling; VerifyPN uses its
unrestricted default configuration.

## Required deployment layout

Common remote workspace: `/home/jules/experiments/pvass-publication`.

Deploy the 24 files of `results/runner-smpt-single-core-v2/source/scripts/` at
those same relative paths, together with its manifest, archive, and provenance.
Create the relative symlink:

```
results/runner-smpt-single-core-v2/source/vendor -> ../../../vendor
```

Helpers and source snapshots keep their isolated source root. The new narrow
`--workspace-root` option checks competing workloads across the common project
root for every solver trial. It does not change SMPT commands or scheduling.
All external tool, interpreter, corpus, result and VerifyPN root paths are
explicit absolute arguments. The vendor symlink supports the runner's inherited
PATH construction; consequently Z3's recorded executable path uses the isolated
vendor alias. The plan and auditor account for that alias explicitly.

Deploy only the selected corpus and its referenced files, new research scripts,
and missing pinned evidence. Reuse existing frozen Linux binaries and tools;
do not overwrite common scripts or same-named native binaries from local copies.
Linux binary identities come from the passed earlier Linux plan/environment.
The plan has 907 runtime/input pins and 33 preflight pins. Its MiniZinc metadata
and bundle manifest transitively pin all 1,136 repaired bundle files, libraries,
configuration, overrides and smoke evidence; the existing pinned read-only
preflight rechecks the closure before execution.

## Capability receipt and launch

Root performs the exact-harness synthetic preflight separately. Save the passed
receipt as `research/general-development-v3-linux-v1/capability.json`, with
`status: "passed"`, this plan's `plan_sha256`, the `runner_archive_sha256`, and
`methods` equal to the plan's nine ordered method labels. Include the substantive
test evidence for EF true/false, AG polarity, fully reducible SMT/CP,
CPU8/cgroup/perf, portable WALK and repaired MiniZinc. The launcher checks receipt
identity; this is not a substitute for reviewing its evidence.

```
vendor/venv/bin/python research/run-general-development-v3-linux-v1.py
vendor/venv/bin/python research/run-general-development-v3-linux-v1.py --launch --capability-receipt research/general-development-v3-linux-v1/capability.json
```

The first command only prints the command. Launch requires the registered Linux
workspace, passed receipt, idle host, all pins, correct symlink, fresh output,
and fresh execution/terminal receipts. Keep its process handle. Observation
failure alone does not establish terminal status; never restart without checking.

After authoritative terminal status, fetch the whole result directory plus
execution, terminal and capability receipts. Then run:

```
vendor/venv/bin/python research/audit-general-development-v3-linux-v1.py
```

The saved-artifact auditor retains the existing complete-matrix, resource,
perf-sidecar, property identity/polarity, independent native check, duplicate,
and family reconciliation. It additionally supports all five SMPT commands,
MCC scheduling metadata, isolated snapshots, common workload scope, and remote
binary identity reporting. Native binary bytes are identified by the prior
passed Linux evidence and launch pins, not by possibly different local binaries.
No external answer becomes an oracle; source-dependent proof checking is not
rerun by this audit. Qualification failures and disagreements block conclusions.

## Identities and mock verification

- Plan SHA256: `7623b77ff5e954b2a5a639f269972bc5016d46038d425a764a9ecd2f96936a74`
- Runner v2 archive SHA256: `44d879b3e87dc028cbf2adc086160cb6c80f5d41dfc2ff1a26abcf3e9a76a659`

`research/test-general-development-v3-linux-v1.py` passes 15 mock/source tests,
including inherited SMPT parsing/command/polarity/preflight cases, explicit
common-root workload checks, unchanged parent controls, and 176/175/1,584
denominators. V1 and historical artifacts remain unchanged.

This is a development qualification screen. Difficulty and superiority remain
unmeasured; one repeat cannot establish stable speed. Preserve every failure,
duplicate and missing counter. Historical survivor execution is separately
incomplete (27/40 rows), and this plan does not reinterpret it as completed.
