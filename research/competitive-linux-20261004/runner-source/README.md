# Isolated competitive runner

Base: `results/runner-smpt-single-core-v3/source/scripts`, the qualified SMPT single-core runner. Its official MCC command and worker policy are retained. `linux_runner.py` remains byte-identical (SHA-256 `413475025b17beaa5a027c6e3495c8dfb0f4898d5e95a79c0f5fe5ad48db5504`). Current project certificate checking dependencies overlay the older snapshot, including grouped-excess and backward-cover. `input-source-provenance.json` records copied inputs; final campaign pins identify edited files.

New behavior:

- `--its-runtime-config PATH` selects `its-mcc`; `its_original.py` stages the one original property and launches the qualified runtime inside the same timed invocation. The harness checks wrapper identity, polarity, timings, exit status, and original tool-log formulas/errors.
- Every published row requires a clean exit and wall time within the requested budget. External errors, capability failures, malformed/conflicting exact-ID formula results, and missing results produce unknown. Rejected observations and exact diagnostics remain in the row and saved logs. External verdicts are tool-reported; only native certificates/witnesses receive independent proof checking.
- Common untimed input/hash preflight requires a single exact property in each XML. VerifyPN consequently uses constant `-x 1`, with its own parsing inside timing.
- The common workspace conflict scanner recognizes Java, ITS, GreatSPN, versioned tool names and the ITS wrapper, while ignoring the harness and independent validation workers.
- The manifest may rebase paths into both original corpora. Rows retain `source_corpus`, `family`, and `family_group`; no copied or translated corpus is required. The root campaign supplies each complete repeat as a separate one-repeat block with a distinct frozen ordering seed.

Local command/parser/timing tests use mocked executors and temporary data; they do not run solvers:

```
PYTHONDONTWRITEBYTECODE=1 vendor/venv/bin/python -m unittest discover -s research/competitive-linux-20261004/runner-source/scripts -p test_competitive_runner.py -v
```

Remote capability qualification and benchmark execution belong to the root campaign. Preserve all sources once the campaign plan is frozen.
