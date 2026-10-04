# Smoke audit repair

The first read-only audit assumed the native-only smoke would snapshot all22
runner files. It failed that assertion because `verifypn_runner.py` is imported
and snapshotted only when VerifyPN is requested. All22runtime files were checked
before the smoke; the21used by this native-only run were correctly snapshotted.
The audit now verifies that exact21-file set and the full22-file preflight
identity. No solver, runner, input, result or benchmark command was changed or
rerun. The corrected audit passed all8rows and reconciled7independent checks.
