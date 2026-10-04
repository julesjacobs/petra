# Diverse SER source families, version 1

The generator `scripts/generate_diverse_ser.py` freezes twelve sources and their hashes in `benchmarks/diverse-ser-programs-v1`. These add two synchronization mechanisms rather than extending the counter, replicas, or phase-monitor ladders. Parameters were fixed before raw exports or solver runs. Difficulty and export feasibility are unmeasured. These are correlated development cases; no reserved MCC family is used.

The source language starts variables at zero; uppercase names are shared and lowercase names are request-local. Execution between explicit `yield` statements is atomic. All variables here have finite domains, but request multiplicity is unbounded. The manifest's serializability expectations are semantic arguments, not mechanically verified ground truth.

## Ring write skew

For rings of 3, 4, and 5 sites, `leave_i` snapshots whether both its own site and its successor are on duty, yields, and conditionally takes its own site off duty. A `reset` request atomically restores every site. Distinct requests overlap on different pairs of shared objects, and resets allow repeated rounds.

In each racy variant, start exactly one request per site before any commits: every snapshot says both sites are on duty. Complete all requests, obtaining success from every site. No serial ordering of exactly these requests has all successes: the last request's successor has already left. There is no reset request in this witness, so serial reordering cannot use reset. This is a cyclic read/write dependency, not a torn read of replicated values.

The protected variant holds both relevant resource locks across snapshot and commit. All requests acquire resource locks in increasing index order; reset acquires all locks in that order. Locks are released only after the operation's final shared-data access. This is strict two-phase locking, giving serializable completed histories, while nonadjacent pairs may proceed concurrently. Increasing acquisition order prevents a lock-wait cycle. Lock release and final response occur in the same atomic segment, so unfinished requests cannot expose committed updates. This is a source-level proof argument; exported queries still require independent checking.

The sites and locks are Boolean. Ignoring reachability restrictions, the racy global data has at most 2^n valuations; the protected global data at most 2^(2n). Request-local snapshot and response values are Boolean. The ladder deliberately stops at five sites to limit frontend growth; even these bounds do not guarantee successful semilinear construction.

## Optimistic validation with epoch wraparound

For odd epoch moduli 3, 5, and 9, `advance` atomically flips a Boolean value and increments a cyclic epoch, then returns zero. `observe` snapshots the value and epoch, yields, reads the value again, and retries until validation succeeds. Its response is the difference between the two values.

The epoch-only variant accepts if the epoch equals the saved epoch. Start one observer, execute exactly d advances during its yield, and resume it. The epoch has returned to its original value, but the Boolean value has changed because d is odd. The observer returns 1 from the zero initial state. A serial observer always returns 0, so the response multiset cannot be reproduced serially. Larger moduli require more interfering advance requests for this particular witness. This is an ABA failure of bounded optimistic validation.

The protected variant also checks that the two observed values agree. It retries instead of exposing an abort response, because abort responses would themselves be absent from serial executions. Every completed observation returns zero and changes no shared data. Every advance also returns zero and runs atomically. Any completed multiset can therefore be reproduced serially with identical responses. Retry divergence is possible and is not claimed to be starvation-free.

Global data has at most 2d valuations; local snapshots range over the same finite domains, with a Boolean retry flag and a response in {-1,0,1}. The protected variant exercises validation and retries without using locks.

## Reproduction and validation status

Run `python3 scripts/generate_diverse_ser.py`. Repeating this command verifies exact frozen bytes; it refuses to overwrite changed output. The manifest uses `ser-stress-sources-v1` and is directly accepted by `scripts/collect_stress_raw.py --manifest benchmarks/diverse-ser-programs-v1/manifest.json --output NEW_DIRECTORY`.

The generator tests check determinism, manifest hashes, immutable output, and the small finite-state schedules used in these arguments. They do not interpret SER or independently verify exported nets. Parsing, raw collection, resource accounting, and backend comparison remain separate steps. Preserve export failures and every original source in the denominator; do not treat missing queries as solved queries.
