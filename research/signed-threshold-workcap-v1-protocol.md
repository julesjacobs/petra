# Higher logical-work diagnostic

Prepared only. No solver run or deployment occurred during preparation.

Selection is exactly the union of the completed full screen's eight historical
native-walk Unknowns and its two unary-only checked answers: ten distinct,
imported queries. It is explicitly outcome-selected. The parent denominator
remains 656 source slots, 640 imports, and 16 unavailable slots. Neither the
selection nor this diagnostic changes the full screen's coverage counts.

The subset manifest references the same original PNML, property XML, and
canonical branch files; no inputs are copied, imported, or changed. Every query
record is identical to its parent record. Logical work increases from 2,000,000
to 100,000,000; this is a solver operation budget, not retired instructions.
The frozen binary, frozen runner, two engines, 5-second solver limit, sampled
2-GiB solver memory limit, separate 60-second/2-GiB checking, order seed, and one
repeat are otherwise unchanged. Expected matrix: 10 × 2 = 20 rows.

## Prepared identities

- Plan: `research/signed-threshold-workcap-v1-plan.json`, SHA256
  `7d2af05b1eb723e5005f9d62083306cae4f642193f04ccd796cf30296de7d639`
- Selection: `research/signed-threshold-workcap-v1-selection.json`, SHA256
  `4d0d1c0cf2ae0d2dd2b76daa636ea44ac9d22efcc4380b825acc8ba755347846`
- Manifest: `benchmarks/signed-threshold-workcap-v1/manifest.json`, SHA256
  `7cc798eb91003e500e59e7445d1c69f22a61e6e1296bc180d3a156af09c5a942`

The plan pins the parent summary/audit/plan, selected inputs, runner and solver
artifacts, interpreter, preparer, launcher, and auditor. Large input/source
digests were inherited from the completed audited full plan during preparation;
the launcher verifies them again before execution. Metadata-only preparation
does not imply those files were rehashed during a concurrent experiment.

## Launch when local work is idle

```
PYTHONDONTWRITEBYTECODE=1 vendor/venv/bin/python research/launch-signed-threshold-workcap-v1.py --launch
```

The launcher refuses existing output/receipt/log artifacts, checks live local
benchmark/build/import workloads, verifies all pins, checks workloads again,
then records execution and terminal receipts. It never kills competing work.
Keep its returned session handle until terminal; do not restart on an
observation timeout. A failed launch that created artifacts requires inspection
and a separately versioned plan, rather than silently overwriting.

## Audit after terminal

```
PYTHONDONTWRITEBYTECODE=1 vendor/venv/bin/python research/audit-signed-threshold-workcap-v1.py
```

This auditor adapts the completed full-screen saved-artifact reconciliation.
It checks selection identity, all 20 unique query/method/repeat cells, command
limits, pinned binary/runner/source/input hashes, both archives, original-input
identity, independent-check requests/responses, every definitive branch proof,
polarity, and resource/deadline status. It preserves Unknowns and validation
failures and emits `research/signed-threshold-workcap-v1-audit.json` with artifact
digests and per-row details. It does not rerun proofs or solvers.

After successful reconciliation, compare each of the 20 outcomes and reasons
with its corresponding saved full-v1 row; report changed coverage, work-limit
versus wall-limit outcomes, and separate solver/checker costs. This selected
diagnostic cannot establish full-cohort superiority or a stable speedup. No
default portfolio change follows automatically from a positive result.

Four metadata/mock tests pass via
`vendor/venv/bin/python research/test-signed-threshold-workcap-v1.py`; they verify
the exact selection, unchanged controls, pin identities, explicit launch guard,
no-overwrite guard, and refusal before process creation on an idle-check failure.
No solver or model import is invoked by those tests.
