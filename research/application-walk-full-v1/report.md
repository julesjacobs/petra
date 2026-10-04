# Complete single-core Linux walk-portfolio comparison

All3280rows pass `audit.json`:656source slots,640imports,16unavailable,
629exact ordered-branch representatives. No answer or duplicate disagreements.
CPU8affinity, enforced2GiB,5s solver budget, one repeat, recorded perf counters;
native original-input translation and witness/proof checks have a separate60s
budget. Allnative definitive answers are independently checked. Competitor
answers are tool-reported.76audit warnings and every resource/collection failure
remain in the artifact.

| Configuration | Definitive imported properties /640 |
|---|---:|
| Native walk portfolio |632|
| Same candidate batched portfolio |615|
| Frozen previous native portfolio |614|
| VerifyPN default |603|
| Repaired SMPT full portable |394|

The walk portfolio gains17properties over matched batched and18over frozen,
with no losses in this run. Against VerifyPN it gains30and loses1:
NoC3x3-PT-8B RC12, reported reachable by VerifyPN. Against SMPT it gains238and
loses none. Complete lists are in `paired-coverage.json`. Sixteen unavailable
TokenRing-50collection slots remain in every source denominator.

Eight native-walk Unknowns remain: NoC3x3-8B RC12, SharedMemory-200
RC01/RC04/RC09/RC12/RC14, and TokenRing-30/40 RC09. Seven are unresolved by every
tested configuration. Unknowns include resource failures and are not claims of
intrinsic reachability hardness.

The previously manual SharedMemory-200 RC03 answer is now also automatic:
this run independently checks branch0by a causal state-equation certificate and
branch1by a633step uniform-walk witness. The manual200step branch3witness remains
valid, but RC03 is no longer a current automatic-solver gap. RC04's manual
negative certificates remain a discovery target. TokenRing-30/40 RC09 have
separate checked phase-pair proofs at30s local limits; those are not included
in this5s Linux portfolio count.

This is development-cohort coverage evidence at a fixed short limit. CPU affinity
is not exclusive isolation; one repeat cannot establish stable timing. The22
reserved families are untouched. No general-superiority, record, novelty or
publication-readiness claim follows. Stronger limits, repeats, representation
strata, ablations and independent family evaluation remain necessary.

## User-space instruction counts

`summarize-instructions.py` reconciles saved full-coverage counters from the passed
audit. On queries where both compared configurations answered definitively:

| Comparator | Pairs | Median native-walk/comparator instructions | Geometric mean ratio |
|---|---:|---:|---:|
| Same candidate batched |615|1.091|2.667|
| Frozen native |614|1.091|2.680|
| VerifyPN default |602|1.346|2.137|
| SMPT full portable |394|0.0139|0.0236|

These are conditional work ratios from one repeat, not unconditional speedups.
All excluded queries are listed in `instruction-summary.json`; new coverage gains
and timeouts are absent from these paired ratios and remain in the full coverage
table. Counts include timed startup/parsing/solver work and exclude independent
native checking. Duplicates are retained. Different returned certificates and
wall-clock budgets can change executed work. In particular, the walk portfolio's
higher coverage does not establish better instruction efficiency than VerifyPN
or its matched native control. Both coverage and overhead must guide subsequent
scheduling changes; no instruction counter removes timeout censorship.
