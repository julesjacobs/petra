# Next SER family: token transfers with early lock release

Propose a **conserved-resource transfer graph** with matched strict-locking and
early-release variants. Unlike the existing ring write-skew family, requests
move resources and expose intermediate writes; correctness depends on retaining
locks across both writes. Unlike optimistic validation, there is no epoch or
retry validation. Difficulty is unmeasured; this is a mechanism proposal, not a
claim of harder exported queries.

## Fixed initial pilot

Use six Boolean slots, exactly two initially occupied, and three interaction
graphs: path0–1–2–3–4–5; that path plus5–0; and that cycle plus0–3,1–4,2–5.
Generate a transfer request in both directions for every edge. Keep the initial
occupied slots0and3 fixed across every graph and variant. This gives six sources
(three graphs times two variants), changing interaction structure while keeping
data domains and initial resource count constant. Freeze all six before export.

The SER sources inspected use zero initialization, uppercase shared variables,
lowercase request-local variables, Boolean expressions, `while`, `if`, and
atomic execution between `yield`s. Emit concrete names and unroll every loop
below except lock waiting; arrays and parameterized requests are pseudocode.
Reuse `request`/ordered-lock emission from `scripts/generate_diverse_ser.py`.

```text
request seed:
    if Ready == 0:
        Occupied0 := 1; Occupied3 := 1; Ready := 1
    return 0                         // no yield anywhere in seed

request transfer_i_j:                 // one per directed edge
    while Ready == 0: yield
    acquire Lock[min(i,j)], then Lock[max(i,j)]
    moved := 0
    if Occupied_i == 1 and Occupied_j == 0:
        Occupied_i := 0
        [unsafe only: release both locks]
        yield
        [unsafe only: reacquire both locks in increasing order]
        Occupied_j := 1               // unsafe deliberately omits revalidation
        moved := 1
    release both locks
    return moved                     // release and return in same atomic segment

request count:
    while Ready == 0: yield
    acquire Lock0, Lock1, ..., Lock5 in increasing order
    answer := Occupied0 + ... + Occupied5
    release all locks
    return answer                    // same atomic segment as release
```

Acquisition emits `while (LockN == 1) { yield }; LockN := 1`. Emit the unsafe
release before the existing yield, and reacquisition after it; neither variant
has an additional data-domain or response change. Evaluate the source condition
inside both locks. The unsafe commit performs no new source debit. Seed writes
only once, never resets live transfers; other requests cannot pass its Ready
guard before initialization. Repeated seed calls return zero without changes.

## Expected semantics

**Strict variant:** every transfer holds both endpoint locks across the debit,
yield and credit. Count holds all slot locks. Increasing lock order excludes
lock-wait cycles, and locks are retained until the final shared access and
response. Strict two-phase locking therefore gives a serial explanation for
completed histories. Between completed transfers exactly two slots are occupied;
count cannot observe a transfer's missing token while it holds those locks.
Incomplete requests and starvation do not imply a completed nonserial history.
This is a source-level argument requiring formal/independent confirmation.

**Early-release variant:** complete one seed; begin transfer0→1, debit slot0,
release its locks and pause at yield; complete count (answer1); then finish the
transfer (answer1). In every completed serial execution of those same requests,
seed must precede the others to pass Ready, transfer preserves two occupied
slots, and count returns2. Thus count's response1 cannot be reproduced by a
serial permutation. No unfinished transfer is needed in this witness. It works
on all three graphs. Further interference may also lose resources through an
overwritten destination; the simple witness avoids relying on that behavior.

## Growth and qualification risks

With six slots there are at most8192shared valuations from six occupancy bits,
six lock bits and Ready, independently of graph density. In general this bound
is `2^(2n+1)`, not a polynomial export guarantee. Request-local domains are
Boolean except count's0..n response. There are12/14/20request types in the
path/cycle/chorded sources, including seed and count. Generated source size is
`O(|E|+n)` apart from identifier lengths. Unbounded request multiplicity remains
part of the raw net. Freeze the initial pilot at six slots; do not extend n
until observed export growth is known.

Use the existing bounded raw-automaton collector with120s per source,2GiB sampled
tree RSS and256MiB sampled artifact cap for this pilot; preserve all failures
and partial files in the six-source denominator. These are operational stopping
limits, not proofs that the exporter respects a mathematical size bound or that
between-sample resource peaks cannot exceed the cap. Do not build serial
semilinear components as a prerequisite. Record source bytes, raw bytes, places,
transitions, automaton states/edges, export duration and any limit reached.

The unsafe cases may be very easy because their witness is short. Safe cases
may also admit small conservation certificates once the appropriate in-flight
control places are included. This is useful diversity even if no timeouts occur.
The central hypothesis is that graph density increases overlap among local
critical sections and the required control projection, rather than merely
increasing token counts. Measure it; do not infer hardness from source size.
Count may introduce a global synchronization bottleneck that makes all safe
variants similarly easy. Retain that result rather than adding arbitrary delays.

Before collecting: independently enumerate the tiny source witness and all its
serial permutations, test seed-before-operation blocking and response labels,
and inspect the exporter's interpretation of a final expression inside each
request. Existing generator tests validate source-level schedules but do not
interpret SER. Unsafe expectations must ultimately have original-query witness
checks; safe expectations must have checked certificates or remain expectations.
No program generation, export, build, solver run or reserved-family inspection
was performed for this design.
