# Relevance reduction: application diagnostic

The matched four-query Linux diagnostic solves the same two properties with
the predecessor and the new relevance reduction, in both repetitions.
VerifyPN solves all four twice. No coverage advantage is established.

On JoinFreeModules-PT-1000 RC01, native median original-input wall time falls
from 1.349 to 0.762 seconds, and median retired instructions from 18.10 to
14.16 billion. VerifyPN takes 0.157 seconds and 1.01 billion instructions.
The reduction helps, but the current native portfolio still spends about
0.6 seconds in earlier phases before its now-small witness search.

CANConstruction is solved by the existing proof phase, while AutoFlight and
DLC remain unknown. The two native configurations each prove CANConstruction
and replay JoinFree witnesses with independent Python checking. There are no
definitive disagreements. Timing variability in prior application diagnostics
is retained, not replaced by this run.

All 24 scheduled rows completed: four previously selected development
properties, three methods, two repeats, shuffled order, five-second original
PNML/XML deadline, CPU8, enforced 2GiB, perf instructions, separately bounded
native checking. Data and binary hashes are in
`results/linux-relevance-diagnostic-v1`; audited counts and per-query medians
are in `research/linux-relevance-diagnostic-v1-analysis.json`.

The next experiment uses all 48 properties of the existing JoinFree development
family, including negatives and previously solved queries, with the standalone
sliced search as a separately named method. Its plan is frozen in
`research/linux-joinfree-relevance-v1-plan.json`. This is development evidence,
not independent evaluation or a general superiority claim.
