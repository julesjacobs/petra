# Phase-partitioned pair closure: four-survivor qualification

The opt-in Rust `phase-pair` method proves both TokenRing properties unreachable,
with independent Python certificate checks on every branch. The two SharedMemory
properties return Unknown because the relation exceeds the configured size cap.
All eight rows and their frozen inputs, binary, source archive, runner archive,
original-input translation checks, validation requests/responses and limits pass
`audit-phase-pair-survivors-v1.py`; reconciliation is saved in
`phase-pair-survivors-v1-audit.json`.

| Original property | Phase-pair | Solver seconds | Separate checker seconds | Same-binary batched + buffer |
|---|---|---:|---:|---|
| TokenRing-PT-030 RC09 (AG) | Unreachable counterexample; property true | 3.900 | 1.355 | 30s timeout |
| TokenRing-PT-040 RC09 (EF) | Unreachable target; property false | 10.981 | 2.695 | 30s timeout |
| SharedMemory-PT-000200 RC03 (AG) | Unknown: relation size limit | 0.438 | — | Memory limit |
| SharedMemory-PT-000200 RC04 (EF) | Unknown: relation size limit | 0.767 | — | Memory limit |

One local repeat, original PNML/XML with parsing included, 30s strict solver
budget, sampled 2GiB memory limit, separate 60s/2GiB/64MiB validation budget.
TokenRing-30 has two checked branches; TokenRing-40 has one. Their complete answer
files occupy 817,374 and 1,164,116 bytes. No branch or failed row is omitted.
Memory-limit rows also have the runner's `outer_timeout` flag set; they are
classified as memory failures here, not as 30 seconds of completed search.

These four cases were selected as survivors of earlier Linux 300s qualification:
464 original slots, 448 imports, 13 selected 60s cases, four selected 300s cases.
All four prior configurations returned Unknown there; several exhausted memory.
This experiment establishes additional checked coverage on those selected cases.
It does not establish a local/Linux speed ratio, broad superiority, or novelty.
The 22 reserved families remain untouched.

The algorithm validates a partition proving global 1-safety, then computes pair
closure in two trace phases: before and after a landmark transition. The checker
requires initial inclusion, inductiveness including preserved pairs across phase
changes, and a target conflict in both phases. Pair abstraction and trace
partitioning are established techniques. Discovery is incomplete and opt-in;
the default portfolio has not changed.

Next: compare phase-partitioned and uniform pair closure on the full ordinary
cohort, retaining all slots and checking every definitive native result. Measure
an integrated portfolio only after identifying its costs and complementary gains.
