# Sparse accelerated-BMC development comparison

All 960 rows passed the saved-artifact audit: 192 properties, five configurations,
one second per property shared across canonical branches. No disagreements or
validation failures. The two unchanged native controls reproduced exactly the same
property answers as the previous screen.

| Configuration | Reachable | Unreachable | Unknown |
|---|---:|---:|---:|
| Ordinary BMC | 67 | 0 | 125 |
| Singleton acceleration | 69 | 0 | 123 |
| Discovered-word acceleration | 69 | 0 | 123 |
| Frozen walk portfolio | 101 | 85 | 6 |
| Earlier frozen portfolio | 98 | 85 | 9 |

The only property-level change from the dense-summary screen is singleton
acceleration gaining TokenRing-PT-005__RC14. Ordinary and discovered-word BMC
reproduce their previous positive sets exactly. All 47 initially satisfied targets
are solved by every configuration. None of the BMC variants adds a positive beyond
either native control; their diagnostic union is still 71 positives.

## What sparse summaries changed

The dense summary cap previously rejected 80 branch attempts across 48 properties
per BMC mode. The sparse candidate eliminates those summary-cap rejections, but
all 80 attempts per mode still end unknown. Outer deadlines expire on 74 ordinary,
73 singleton, and 75 discovered-word attempts; the depth-dependent encoding cap
accounts for five, six, and five attempts respectively. No memory-limit failure
occurs on this subset. One ordinary attempt reports an encoding deadline.

Saved phase artifacts show SMT invocations at the newly accessible depths, usually
one, two, or four. They do not measure phase durations. Consequently these logs
cannot distinguish SMT search cost from formula construction and process overhead.
The sparse implementation removes a real representation limit, but this screen
shows no substantial coverage benefit. Further static vocabulary tuning is not
yet justified by these results.

Next experiment: reuse a persistent incremental SMT instance and Rust summaries,
then learn bounded original-transition words from feasible prefix models. Separate
incrementality from learning in ablations, record per-phase costs, and retain
independent compressed checking. Keep bounded UNSAT as unknown; do not introduce
safety blocking without its coverage proof. This is adaptation of published ABMC
ideas, not a novelty claim or an implemented improvement yet.

## Evidence and limitations

Plan SHA256: 7895a8c918a2ad7a1b8a88900d85d6a817640a2fd6f64f42cfe843e9f5a80f31.
Runs SHA256: f4636f152faf491c920ba4d676f0a1701e03b20fefd60c4b0916bbf7d9e39118.
See audit.json, diagnostics.json, paired-comparison.json, and
previous-cap-followthrough.json. Frozen candidate is
results/solver-abmc-mcc-sparse-v1; complete raw results are in
results/abmc-mcc-sparse-v1. Previous evidence is unchanged.

This is one shared-macOS development repeat with sampled process-tree memory limits,
independent checking outside solver timing, and canonical inputs. No concurrent
local build or solver experiment ran; lightweight inspection and script editing
continued. No stable speed, held-out generalization, superiority, or publication
readiness claim follows. The default portfolio remains unchanged.
