# Bounded-group pilot: no coverage gain

All 24 registered rows completed; artifact reconciliation passed. The structural,
single-coordinate and bounded-group methods each prove 2/4 queries at 20 million
work and 3/4 at two billion work. All 15 definitive answers passed independent
checking; no verdict disagreement occurred. n5 remains unresolved.

Limits were 30 seconds including input and checking, sampled 2 GiB, one repetition
and one invocation at a time. The same frozen binary serves all three methods.
These are local diagnostics, not stable competitive timings. Raising the work
tier increases both solver and checker work.

The grouped method finds three-place supports on n3, but its final checked
certificate still has the structural projection's 120 places and 362 nodes.
On n4/n5 it certifies a singleton, then exhausts the 128-proposal cap while
seeking a group for the next chosen guard. This says nothing about other guards
or existence of a larger support. At the standard n5 budget the refinement slice
cannot afford setup. At expanded work, n5's grouped method reaches about 1998 MiB
and returns Unknown at its work cap; the structural baseline crosses 2 GiB.
No solve gain follows from avoiding that memory-limit outcome.

The implementation searches 0/1 supports with at most 32 places and 128 proposals,
using exact original weighted-arc inequalities. Complete supports are retained,
including zero-mass supports; their union need not have a nonincreasing indicator.
All preparation, proposal, exact checking and union work consume the refinement
reservation. Initial masses are computed but not logged. The existing original
query certificate checkers remain unchanged. Some diagnostic logs hit their cap;
unfinished phases remain censored.

Validation: 202 library tests, seven CLI tests (covering both new methods), three
diagnostic integration tests, two schema tests, 20 Python harness tests,
formatting, Clippy and release build pass. Existing vendor warnings remain.

Frozen binary: `results/solver-raw-adaptive-groups-v1/vass-reach`, SHA-256
`7549042b1367442209cc33e77210c08bbd2bb2fbcb4e3d4a21afcd626ff2375d`.
See `raw-adaptive-groups-pilot-v1-plan.json`, `-analysis.json`, `-verification.json`
and `raw-adaptive-groups-review-v1.md`.

A separate memory experiment will share exact control markings across game nodes
and the identity map. Saved n4 certificate data contain 3968 nodes but only 453
distinct control markings. This motivates interning, but does not establish full
game compression, RSS attribution, or n5 improvement. Certificate serialization
and the independent checker will retain their existing representation.
