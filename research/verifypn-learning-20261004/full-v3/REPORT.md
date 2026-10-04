# VerifyPN-inspired native development comparison

Contended full development coverage pilot; no speed claim.

Descriptive only; no speed claim.

| Method | Repeat 1 | Repeat 2 | Both | Either |
|---|---:|---:|---:|---:|
| candidate | 364/368 | 364/368 | 364 | 364 |
| baseline | 363/368 | 363/368 | 363 | 363 |

Stable paired gains/losses: **1/0**. All 1472 rows retained.

Per-corpus, per-family, original-property and ordered-branch representative views, failure counts, PAR2 and separate checking costs are in `summary.json`.

Accepted answers were independently checked against original PNML/XML and every canonical branch during measurement. This audit inspects the saved evidence and does not rerun certificate checking.

Build correspondence: `supplied-build-receipt`.

- Portable solver and validator memory/CPU metrics are sampled; short-lived children may escape samples.
- Portable wall time includes cleanup; Linux solver wall time ends before final cleanup.
- Host samples detect observed contention; they do not establish exclusive CPUs or rule out between-sample interference.
- Source/binary correspondence is unverified without a supplied build receipt; receipts are not reproducible-build verification.
