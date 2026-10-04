# Isolated SMPT configuration runner

Prepared `results/runner-smpt-single-core-v1` from the 24 hash-verified files in
`results/runner-threshold-v1/source`. Only `scripts/benchmark_smpt_classic.py`
differs. Shared scripts and parent artifacts are unchanged. No experiment has
been frozen, deployed, or executed with this runner.

Added configurations:

| Label | Requested policy |
|---|---|
| smpt-compact-portable | WALK STATE-EQUATION BMC K-INDUCTION SMT |
| smpt-pdr-reach-portable | PDR-REACH SMT |
| smpt-pdr-saturated-portable | PDR-REACH-SATURATED SMT |
| smpt-mcc-portable | Official --mcc |

All four require resource tracking, `reduce`, `walk`, `qsolve`, `z3`, and the
hash-checked portable WALK patch. All enable automatic reduction. None enables
projection. MCC also passes the full requested method list because SMPT's CLI
requires one method-group option; official MCC scheduling ignores that list.
Row and environment metadata distinguish requested methods, scheduling policy,
and unknown effective workers. Unavailable slots retain scheduling metadata.

Added configurations reject expired or over-budget answers on either platform.
Original configurations retain their commands, parsing, and timeout behavior.
Property polarity and exact escaped property IDs are preserved. New rows select
the matching property's FORMULA line for audit metadata.

## Verification

`PYTHONDONTWRITEBYTECODE=1 vendor/venv/bin/python research/test-smpt-single-core-runner-v1.py`
passes 13 tests (including parameterized cases); log:
`research/smpt-single-core-runner-v1-test.log`. Calls to the benchmark executor
and dependency-help subprocess are mocked. Parser tests execute only the AST
slice constructing SMPT's real argument parser, without importing SMPT or models.
No solver, build, model import, or external dependency was run. Tests cover
commands, real argparse acceptance, EF/AG polarity, wrong property IDs,
contradictory answers, late output, capability reporting, required preflight,
environment/unavailable row metadata, and parent command/result equivalence.
A second preparation in a temporary directory produces byte-identical archive
and provenance. Existing runner hashes remain unchanged.

An initial mock test failed because `platform.platform()` also used the mocked
subprocess API; the assertion now counts the specific `walk -h` dependency-help
call. The first MCC draft omitted the required `--methods`; source inspection
caught this before completion, and the real-parser regression covers it.

## SHA256

- New benchmark script: `fcd748b0f92178dca63d87e279b9b3e0795c3cf90aac4b25ad060e7f91dd8fed`
- Deterministic runner archive: `5ad4ebe9557775469544182d51e9b9aa8e8e60300fea107aa2b0104ca4eae20d`
- Preparer: `429fe061f5433809a6ef745e9858993f125bd28a6de0ea071cb472f8a3cc94f9`
- Test source: `6fe86c51023f770e42355b437d8a505c201b76bb2f39959b6d4cf64926497c7e`

Complete file digests, parent digests, and change scope are in the runner's
`files-sha256.json` and `provenance.json`. This establishes harness behavior
under mocks, not competitor capabilities or performance on real models.
