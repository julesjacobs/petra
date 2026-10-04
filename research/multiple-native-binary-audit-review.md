# Multiple native binary and flag registration

Implemented in `scripts/analyze_application_expansion.py` and `research/audit-linux-application-expansion-v1.py`. Production runner, plans, frozen results and existing reports were not edited.

The analyzer now resolves the explicit `native_tools` map per native label, checks each registered engine against `methods`, and requires exact agreement with environment binary paths and hashes. It rejects missing/extra labels, malformed paths, conflicting hashes for one path, and a missing/ambiguous primary candidate. Legacy plans still resolve every native label to the single registered binary. The workspace is derived from the primary candidate's existing workspace-relative `native_binary` and its matching absolute registration; the Linux auditor additionally requires its fixed Linux workspace.

The four optional method lists are validated as unique native labels. Missing lists mean empty lists; recorded environment lists must agree. Exact native command checking covers binary, PNML, XML, property ID, engine, time, state cap, and every optional flag in runner order. Missing, duplicate, reordered or additional options fail. Unavailable collection slots retain their full denominator and never require a solver command.

The Linux auditor no longer assumes labels `native-focused`/`native-symbolic` or one native binary. Every explicit binary must be in `required_file_sha256`; locally fetched/frozen bytes are checked under the existing artifact policy. Every environment-declared runner snapshot is checked against fetched bytes. For the new explicit-map schema, every snapshot must also be plan-pinned, including `kreach_adapter.py`. The mechanism handles the runner's new 22-file dependency set without a fixed count or live-source substitution. Historical plans retain their previous registration policy.

Validation: 26 tests pass in the two existing test modules. New cases cover three native configurations over two binaries, all four flags, binary/engine/hash drift, unregistered flags, command mutation, primary-candidate mismatch, missing predecessor identity, missing runtime snapshot, and a 656-slot / 640-imported / 3,280-row denominator. Existing 192-query legacy artifact tests continue to pass. Tests run locally and execute no solvers.

Read-only reanalysis of the existing 768-row application expansion and 1,856-row parameter ladder accepts their legacy native commands and preserves all existing coverage summaries, validity, row flags and denominators. The older expansion report predates two collection-summary fields already present before this change, so comparison used its existing fields. Existing report files were not regenerated; its historical invalid-answer status remains unchanged.

Commands:

```sh
PYTHONPATH=scripts python3 -m unittest scripts.test_analyze_application_expansion scripts.test_application_artifact_audit
```

No solver, proof checker, Cargo, deployment, transfer or remote operation was run. Parent review and the new registered benchmark remain outstanding.
