# Longer-budget application qualification

Current status:60s complete and audited;9/13cases recovered by at least one method.
The4joint survivors are registered at300s,16rows, running session81844.
No Linux engineering, builds, imports or bulk transfer until it is terminal.
Use `audit-linux-application-expansion-v2.py` for subsequent artifact auditing.
The original v1 audit failure and `audit-role-erratum.json` are retained;
`advance-application-qualification-v2.py` registered300s after the corrected audit.
Do not rerun initial registration or advancement commands below.

The following is the original protocol, retained for context.

Prepared locally only. Nothing has been deployed or launched. Do not run this
while the full Linux comparison is active. All files in this directory and the
two qualification Python scripts are new; the full comparison plan is unchanged.

The 60-second stage includes **all 13 originally jointly unresolved properties**:
eight SharedMemory-200 and five TokenRing-30/40 properties. Selection comes from
the frozen earlier ladder analysis, irrespective of the new comparison's
outcomes. `selection.json` preserves all 52 original selected rows, their flags,
the 64 parent collection-failure rows, and source identities. Parent denominators
remain **464 slots, 448 imports, 442 exact representatives, 16 collection failures**.
Those collection failures are not silently rerun or counted as selected imports.

`plan-60.json` registers 52 rows: native focused+buffer, native batched+buffer,
VerifyPN default, and repaired SMPT full portable, each once on every query.
The two native configurations use the frozen Linux repeated-search binary
`876e855affc6aab53f920295dcb57747df7de61bbb64733d89b63ff8c9aa0ab5`.
The existing frozen 22-file runner closure, independent checker limits and tool
identities are inherited from the full comparison. Both native configurations
enable buffer agglomeration; other experimental preprocessing flags are off.
Limits are CPU8, perf, aggregate 2 GiB, two million states and a strict outer
deadline. Independent native checking is separately bounded at 60 seconds,
2 GiB and 64 MiB response size, excluded from solver timing. Validation failure
counts as unresolved. Competitor answers remain tool-reported.

Print the exact registered 60-second command without executing it:

```sh
python3 research/run-application-ladder-qualification-v1.py --stage 60
```

After the current comparison is confirmed terminal, deploy these new research
files, verify the registered hashes, and launch explicitly on Linux:

```sh
vendor/venv/bin/python research/run-application-ladder-qualification-v1.py \
  --stage 60 --launch --terminal-predecessor CONFIRMED_COMPLETED_SESSION_ID
```

The launcher requires the registered Linux path, checks workspace workloads,
all registered file hashes and the MiniZinc repair preflight, and refuses an
existing output directory. The predecessor argument records the operator's
confirmation; it does not independently inspect another session. Record the
launch log. Transfer/development work must finish before measurement starts.

After the 60-second run is confirmed terminal, retrieve its complete artifacts.
Create a local completion receipt with this structure and actual values:

```json
{
  "terminal": true,
  "session_id": "CONFIRMED_COMPLETED_SESSION_ID",
  "exit_code": 0,
  "output": "results/linux-application-ladder-qualification-v1-60",
  "sha256": {"environment.json": "ACTUAL_SHA256", "runs.jsonl": "ACTUAL_SHA256"}
}
```

The recorded exit code may be nonzero: a harness error is preserved, not treated
as a solver verdict or sufficient evidence that the matrix is unusable.
Run the local advancement command once:

```sh
python3 research/prepare-application-ladder-qualification-v1.py \
  --advance-after-terminal-60 research/qualification-60-completion.json
```

This reruns the artifact consistency audit without running a solver, retains
its full report, and refuses incomplete/invalid/conflicting evidence. It then
registers `plan-300.json` and its exact manifest containing every query with no
strictly accepted definitive answer from any of the four methods. Timeouts,
OOM, checker failures and operational errors remain eligible; error cases are
not filtered out to improve the success rate. All original selections and
60-second rows remain preserved. If none survive, the new plan records zero
invocations. Otherwise deploy the new stage files only while Linux is idle and
use the same launcher with `--stage 300` and the completed 60-second session ID.
There is no automatic chaining of experiments.

Report recovery at 60 seconds over all 13 selected cases, then recovery at
300 seconds over the registered joint survivors; also retain their relation
to the 464-slot parent. Do not merge these timings into the five-second result.
Selection is outcome-dependent and favors cases that defeated the earlier
configurations. It supports development qualification, not general superiority,
held-out performance, or intrinsic hardness claims. All 13 original cases had
recorded timeout/error flags. A killed invocation usually lacks complete phase
timing: parsing, reduction, search and witness costs cannot be inferred from
its elapsed time. Attribute these costs only where saved uncensored phase
evidence supports it. Longer timeouts with the same state cap can still stop at
the state cap; classify those separately. Instruction counts do not remove
contention, timeout censorship or insufficient counter coverage.
