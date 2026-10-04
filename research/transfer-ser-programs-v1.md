# Resource-transfer SER programs

`scripts/generate_transfer_ser.py` defines a fixed12-source ladder:4and6Boolean
slots, path/cycle/chorded graphs, and strict/early-release locking. Chorded means
a cycle plus all opposite-vertex edges. Each undirected edge supplies both
directed transfer requests; seed and count are additional requests. Initially
seed places exactly two resources at slots0andn/2. Four-slot members are new
export-feasibility bridges, not duplicates of existing benchmarks. Every source
must remain in the12-source denominator regardless of export or solver outcome.

Seed is atomic and initializes only once. Other operations wait until Ready.
A transfer acquires its endpoint locks in increasing order, checks for an occupied
source and empty destination, debits the source, yields, credits the destination,
then releases locks and responds in one atomic segment. The strict variant holds
both locks throughout. The early-release variant releases both before the yield
and reacquires them before the credit, deliberately without revalidation. Count
holds all locks in increasing order while summing occupancies and releases them
in its response segment. Generated SER uses concrete variable/request names and
the existing `request` formatter; no arrays or parameterized syntax are required.

Strict variants are expected serializable by strict two-phase locking. Seed's
Ready publication precedes all shared-data operations, and later seeds are no-ops.
Incomplete transfer writes stay protected, and increasing acquisition order
excludes lock-wait cycles. The argument does not claim starvation freedom.

Every early-release variant has the same completed unsafe schedule: seed;
transfer0→1 debits and yields; count returns1; transfer commits and returns1.
In every completed serial ordering of those same three operations, seed must
precede the other operations and count returns2. Thus the observed responses
cannot be reproduced serially. No reset or unfinished operation is needed.
These expectations remain source-level arguments, not solver ground truth or
mechanically checked exported-net results.

The finite-schedule tests independently model lock ownership, partial acquisition,
yield points, seed blocking and responses. They compare strict interleavings of
two transfer invocations plus count/seed against serial permutations for all
directed edge pairs of both chorded sizes (covering the smaller graphs' edges).
They also check the completed unsafe witness, repeated seed behavior, emitted
critical lock scopes, graph structure, deterministic manifests and immutable
output. This finite model is not a SER interpreter and does not prove the
unbounded-request theorem or validate frontend translation.

Source size isO(|E|+n), excluding identifier lengths. Shared-state valuation
bounds are512atn=4and8192atn=6, from2n+1Boolean variables; these are not measured
Petri-net sizes or polynomial export bounds. Request types are8/10/14for the
four-slot graphs and12/14/20for six slots. Request multiplicity remains unbounded.
Increasing density changes critical-section overlap while keeping initial token
count fixed. Both safe proofs and unsafe witnesses might be easy; difficulty and
export feasibility are unmeasured. Count's global locking may dominate the
interaction structure. Preserve easy outcomes rather than adding artificial work.

All eight generator/semantic tests pass. No export, build or solver has been run
for this family. Reproduce tests and the immutable source freeze with:

```sh
vendor/venv/bin/python -m unittest discover -s scripts -p 'test_generate_transfer_ser.py' -v
vendor/venv/bin/python scripts/generate_transfer_ser.py
```

The generator writes `benchmarks/transfer-ser-programs-v1`, including source
hashes, pair links, structural bounds, generator/test/parser provenance and the
`ser-stress-sources-v1` manifest accepted by the existing collector. Repeating
generation verifies exact bytes; changed existing output is rejected without
overwriting it. No export or solver is invoked by generation. Freeze all12before
collecting four-slot members first, then six-slot members. Use separately
registered resource limits and retain collection failures and partial artifacts.
Original-query witness checks and checked negative certificates are required
before reporting any source expectation as a verified answer.
