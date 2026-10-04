# Parameterized SER programs

`scripts/generate_harder.py` deterministically writes 24 programs and a SHA256 manifest in `benchmarks/harder-programs`. These are candidate harder workloads, not a claim that every generated query is difficult. All data domains are finite; the number of outstanding requests remains unbounded. Uppercase variables are shared, lowercase variables are request-local, and execution is atomic between explicit `yield` operations, as in the artifact examples.

| Family | Parameters | Programs | Expected source status |
|---|---|---:|---|
| Cyclic counter | domain/stages = 3/1, 5/2, 7/3, 17/8 | 8 | racy nonserializable; locked serializable |
| Replicated register | 2, 3, 4, 6 Boolean cells | 8 | racy nonserializable; locked serializable |
| Phase monitor | domain 2 or 3 with 2/4/6 cycles; domains 3/4 with 12 cycles | 8 | nonserializable |

The manifest records **source-program expectations**, justified below. Each raw export is one whole-program counterexample query: nonserializability corresponds to reachability. These arguments have not been mechanically checked by an independent SER semantics interpreter; benchmark positives are separately checked against the exported net and target.

## Cyclic counter

`incr` reads a bounded cyclic counter, executes a finite sequence of yield stages while retaining the read value, then writes and returns the new value. Concurrent instances of this request interact through the shared counter. Increasing the domain adds global states and snapshot values; increasing stages adds genuinely reachable request continuations while a stale value remains live. Wraparound preserves a finite domain even under races.

For each racy variant, start two `incr` requests at X=0, let both save 0, then let both complete. Both responses are 1. A serial execution with exactly those two requests instead returns 1 and 2 (all generated domains are at least 3), in either order. Thus the source is nonserializable.

Locked variants hold a single shared lock across the yielding stages, including the initial read and final update. The wait condition, acquisition, and first body segment occur in one atomic segment. Only its owner releases the lock; no request touches X without owning it. Ordering completed requests by their lock acquisitions gives the serial execution with identical responses. A pending final owner cannot affect any later completed operation. Thus these variants are serializable. The yield stages remain reachable and generate suspended requests and contention.

## Replicated register

A `write` chooses the complement of the first cell and copies that value into every cell, yielding between cells. `read` returns the binary encoding of all cells. Increasing the cell count introduces interacting shared data, additional reachable intermediate configurations, and more distinct responses. Expressions use repeated addition because SER has no multiplication operator.

In a serial execution the cells always agree. A read returns either 0 or 2^n−1. Starting from all-zero cells, suspend the first write after it sets Cell0=1, issue a read returning 1, then finish the write. For n≥2 this read response is impossible serially, so every racy variant is nonserializable.

In locked variants both write and read hold the same lock. The same lock-order argument as above proves serializability, even though a write yields while holding the lock. Writers interact through their shared first cell and may retain a stale chosen value in racy variants; the programs are not independent duplicated components.

## Phase monitor

`advance` increments a shared cyclic phase and returns 0. `observe` requires a sequence of phases 1,…,d−1,0 repeated c times, yielding while waiting for each required phase, then returns 100. Its local countdown and phase position produce distinct reachable continuations.

A serial `observe` cannot finish: with no interleaved advance the phase is constant, but every cycle requires at least two distinct phase values. Concurrently, schedule the observer between each advance; d×c advances suffice to complete it. Its response 100 therefore witnesses nonserializability. These instances exercise finite control and witnesses requiring successively more interacting requests (4 to 48 advances), rather than merely extra dead branches.

## Reproduction and interpretation

Run `python3 scripts/generate_harder.py`. The generated sources have no random choices. Preserve the manifest and source hashes with collection results. Collect the same sources through the raw-query exporter before comparing backend methods; source expectations are sanity checks for a complete collection, not substitutes for witness or certificate verification. Record frontend timeouts separately: missing queries are not solved queries and do not establish serializability.

## Frontend smoke check

All 24 final programs parsed and exported successfully with `ser --no-viz --export-raw SOURCE.ser`; elapsed times are recorded in `benchmarks/harder-programs/smoke.json` (not solver performance measurements). An initial counter design with increment, decrement, and read requests exceeded the existing serial-language semilinear construction limit, so the final counter family uses increment requests only. The replicated-register family retains interacting read/write operations. The raw exporter still needs to compute the serial language to define its target, and this limit belongs to that necessary frontend construction.
